// Voice assistant example
//
// Speak short text commands to the microphone.
// This program will detect your voice command and convert them to text.
//
// Trimmed version of https://github.com/ggerganov/whisper.cpp/tree/master/examples/command
//

#include "common-sdl.h"
#include "common.h"
#include "whisper.h"
#include "httplib.h"

#include <sstream>
#include <cassert>
#include <cstdio>
#include <fstream>
#include <mutex>
#include <regex>
#include <string>
#include <thread>
#include <vector>
#include <map>

// command-line parameters
struct whisper_params {
    int32_t n_threads  = std::min(4, (int32_t) std::thread::hardware_concurrency());
    int32_t prompt_ms  = 5000;
    int32_t command_ms = 8000;
    int32_t capture_id = -1;
    int32_t max_tokens = 32;
    int32_t audio_ctx  = 0;

    float vad_thold  = 0.6f;
    float freq_thold = 100.0f;

    float grammar_penalty = 100.0f;

    grammar_parser::parse_state grammar_parsed;

    bool speed_up      = false;
    bool translate     = false;
    bool print_special = false;
    bool print_energy  = false;
    bool no_timestamps = true;
    bool use_gpu       = true;

    std::string language  = "en";
    std::string model     = "models/ggml-base.en.bin";
    std::string fname_out;
    std::string commands;
    std::string prompt;
    std::string context;
    std::string grammar;

    // A regular expression that matches tokens to suppress
    std::string suppress_regex;

    std::string rag_url = "localhost:8085";
};

void whisper_print_usage(int argc, char ** argv, const whisper_params & params);

bool whisper_params_parse(int argc, char ** argv, whisper_params & params) {
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];

        if (arg == "-h" || arg == "--help") {
            whisper_print_usage(argc, argv, params);
            exit(0);
        }
        else if (arg == "-t"   || arg == "--threads")       { params.n_threads     = std::stoi(argv[++i]); }
        else if (arg == "-pms" || arg == "--prompt-ms")     { params.prompt_ms     = std::stoi(argv[++i]); }
        else if (arg == "-cms" || arg == "--command-ms")    { params.command_ms    = std::stoi(argv[++i]); }
        else if (arg == "-c"   || arg == "--capture")       { params.capture_id    = std::stoi(argv[++i]); }
        else if (arg == "-mt"  || arg == "--max-tokens")    { params.max_tokens    = std::stoi(argv[++i]); }
        else if (arg == "-ac"  || arg == "--audio-ctx")     { params.audio_ctx     = std::stoi(argv[++i]); }
        else if (arg == "-vth" || arg == "--vad-thold")     { params.vad_thold     = std::stof(argv[++i]); }
        else if (arg == "-fth" || arg == "--freq-thold")    { params.freq_thold    = std::stof(argv[++i]); }
        else if (arg == "-su"  || arg == "--speed-up")      { params.speed_up      = true; }
        else if (arg == "-tr"  || arg == "--translate")     { params.translate     = true; }
        else if (arg == "-ps"  || arg == "--print-special") { params.print_special = true; }
        else if (arg == "-pe"  || arg == "--print-energy")  { params.print_energy  = true; }
        else if (arg == "-ng"  || arg == "--no-gpu")        { params.use_gpu       = false; }
        else if (arg == "-l"   || arg == "--language")      { params.language      = argv[++i]; }
        else if (arg == "-m"   || arg == "--model")         { params.model         = argv[++i]; }
        else if (arg == "-f"   || arg == "--file")          { params.fname_out     = argv[++i]; }
        else if (arg == "-cmd" || arg == "--commands")      { params.commands      = argv[++i]; }
        else if (arg == "-p"   || arg == "--prompt")        { params.prompt        = argv[++i]; }
        else if (arg == "-ctx" || arg == "--context")       { params.context       = argv[++i]; }
        else if (arg == "-url" || arg == "--rag-url")       { params.rag_url       = argv[++i]; }
        else {
            fprintf(stderr, "error: unknown argument: %s\n", arg.c_str());
            whisper_print_usage(argc, argv, params);
            exit(0);
        }
    }

    return true;
}

void whisper_print_usage(int /*argc*/, char ** argv, const whisper_params & params) {
    fprintf(stderr, "\n");
    fprintf(stderr, "usage: %s [options]\n", argv[0]);
    fprintf(stderr, "\n");
    fprintf(stderr, "options:\n");
    fprintf(stderr, "  -h,         --help           [default] show this help message and exit\n");
    fprintf(stderr, "  -t N,       --threads N      [%-7d] number of threads to use during computation\n", params.n_threads);
    fprintf(stderr, "  -pms N,     --prompt-ms N    [%-7d] prompt duration in milliseconds\n",             params.prompt_ms);
    fprintf(stderr, "  -cms N,     --command-ms N   [%-7d] command duration in milliseconds\n",            params.command_ms);
    fprintf(stderr, "  -c ID,      --capture ID     [%-7d] capture device ID\n",                           params.capture_id);
    fprintf(stderr, "  -mt N,      --max-tokens N   [%-7d] maximum number of tokens per audio chunk\n",    params.max_tokens);
    fprintf(stderr, "  -ac N,      --audio-ctx N    [%-7d] audio context size (0 - all)\n",                params.audio_ctx);
    fprintf(stderr, "  -vth N,     --vad-thold N    [%-7.2f] voice activity detection threshold\n",        params.vad_thold);
    fprintf(stderr, "  -fth N,     --freq-thold N   [%-7.2f] high-pass frequency cutoff\n",                params.freq_thold);
    fprintf(stderr, "  -su,        --speed-up       [%-7s] speed up audio by x2 (reduced accuracy)\n",     params.speed_up ? "true" : "false");
    fprintf(stderr, "  -tr,        --translate      [%-7s] translate from source language to english\n",   params.translate ? "true" : "false");
    fprintf(stderr, "  -ps,        --print-special  [%-7s] print special tokens\n",                        params.print_special ? "true" : "false");
    fprintf(stderr, "  -pe,        --print-energy   [%-7s] print sound energy (for debugging)\n",          params.print_energy ? "true" : "false");
    fprintf(stderr, "  -ng,        --no-gpu         [%-7s] disable GPU\n",                                 params.use_gpu ? "false" : "true");
    fprintf(stderr, "  -l LANG,    --language LANG  [%-7s] spoken language\n",                             params.language.c_str());
    fprintf(stderr, "  -m FNAME,   --model FNAME    [%-7s] model path\n",                                  params.model.c_str());
    fprintf(stderr, "  -f FNAME,   --file FNAME     [%-7s] text output file name\n",                       params.fname_out.c_str());
    fprintf(stderr, "  -cmd FNAME, --commands FNAME [%-7s] text file with allowed commands\n",             params.commands.c_str());
    fprintf(stderr, "  -p,         --prompt         [%-7s] the required activation prompt\n",              params.prompt.c_str());
    fprintf(stderr, "  -ctx,       --context        [%-7s] sample text to help the transcription\n",       params.context.c_str());
    fprintf(stderr, "  -url,       --rag-url        [%-7s] url of tasya-rag server\n",                     params.rag_url.c_str());
    fprintf(stderr, "\n");
}

std::string transcribe(
                 whisper_context * ctx,
            const whisper_params & params,
        const std::vector<float> & pcmf32,
               const std::string & grammar_rule,
                           float & logprob_min,
                           float & logprob_sum,
                             int & n_tokens,
                         int64_t & t_ms) {
    const auto t_start = std::chrono::high_resolution_clock::now();

    logprob_min = 0.0f;
    logprob_sum = 0.0f;
    n_tokens    = 0;
    t_ms = 0;

    //whisper_full_params wparams = whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
    whisper_full_params wparams = whisper_full_default_params(WHISPER_SAMPLING_BEAM_SEARCH);

    wparams.print_progress   = false;
    wparams.print_special    = params.print_special;
    wparams.print_realtime   = false;
    wparams.print_timestamps = !params.no_timestamps;
    wparams.translate        = params.translate;
    wparams.no_context       = true;
    wparams.no_timestamps    = params.no_timestamps;
    wparams.single_segment   = true;
    wparams.max_tokens       = params.max_tokens;
    wparams.language         = params.language.c_str();
    wparams.n_threads        = params.n_threads;

    wparams.audio_ctx = params.audio_ctx;
    wparams.speed_up  = params.speed_up;

    wparams.temperature     = 0.4f;
    wparams.temperature_inc = 1.0f;
    wparams.greedy.best_of  = 5;

    wparams.beam_search.beam_size = 5;

    wparams.initial_prompt = params.context.data();

    wparams.suppress_regex = params.suppress_regex.c_str();

    if (whisper_full(ctx, wparams, pcmf32.data(), pcmf32.size()) != 0) {
        return "";
    }

    std::string result;

    const int n_segments = whisper_full_n_segments(ctx);
    for (int i = 0; i < n_segments; ++i) {
        const char * text = whisper_full_get_segment_text(ctx, i);

        result += text;

        const int n = whisper_full_n_tokens(ctx, i);
        for (int j = 0; j < n; ++j) {
            const auto token = whisper_full_get_token_data(ctx, i, j);

            if(token.plog > 0.0f) exit(0);
            logprob_min = std::min(logprob_min, token.plog);
            logprob_sum += token.plog;
            ++n_tokens;
        }
    }

    const auto t_end = std::chrono::high_resolution_clock::now();
    t_ms = std::chrono::duration_cast<std::chrono::milliseconds>(t_end - t_start).count();

    return result;
}

std::vector<std::string> get_words(const std::string &txt) {
    std::vector<std::string> words;

    std::istringstream iss(txt);
    std::string word;
    while (iss >> word) {
        words.push_back(word);
    }

    return words;
}

// always-prompt mode
// transcribe the voice into text after valid prompt
int always_prompt_transcription(struct whisper_context * ctx, audio_async & audio, const whisper_params & params) {
    bool is_running = true;
    bool ask_prompt = true;

    float logprob_min = 0.0f;
    float logprob_sum = 0.0f;
    int   n_tokens    = 0;

    std::vector<float> pcmf32_cur;

    const std::string k_prompt = params.prompt;

    const int k_prompt_length = get_words(k_prompt).size();

    fprintf(stderr, "\n");
    fprintf(stderr, "%s: always-prompt mode\n", __func__);

    // main loop
    while (is_running) {
        // handle Ctrl + C
        is_running = sdl_poll_events();

        // delay
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        if (ask_prompt) {
            fprintf(stdout, "\n");
            fprintf(stdout, "%s: The prompt is: '%s%s%s'\n", __func__, "\033[1m", k_prompt.c_str(), "\033[0m");
            fprintf(stdout, "\n");

            ask_prompt = false;
        }

        {
            audio.get(2000, pcmf32_cur);

            if (::vad_simple(pcmf32_cur, WHISPER_SAMPLE_RATE, 1000, params.vad_thold, params.freq_thold, params.print_energy)) {
                fprintf(stdout, "%s: Speech detected! Processing ...\n", __func__);

                int64_t t_ms = 0;

                // detect the commands
                audio.get(params.command_ms, pcmf32_cur);

                wav_writer wavWriter;
                wavWriter.open("input.wav", WHISPER_SAMPLE_RATE, 16, 1);
                wavWriter.write(pcmf32_cur.data(), pcmf32_cur.size());

                const auto txt = ::trim(::transcribe(ctx, params, pcmf32_cur, "", logprob_min, logprob_sum, n_tokens, t_ms));

                const auto words = get_words(txt);

                std::string prompt;
                std::string command;

                bool found_prompt = false;
                float sim = 0.0f;
                for (int i = 0; i < (int) words.size(); ++i) {
                    fprintf(stdout, "%s\n", words[i].c_str());
                    if (found_prompt) {
                        command += words[i] + " ";
                        continue;
                    }
                    sim = similarity(words[i], k_prompt);
                    if (sim > 0.7f) {
                        found_prompt = true;
                        prompt += words[i] + " ";
                    }
                }

                //debug
                // fprintf(stdout, "prompt sim: %f\n", sim);
                // fprintf(stdout, "command size: %i\n", command.size());
                // fprintf(stdout, "prompt word: %s\n", prompt.c_str());

                if ((sim > 0.7f) && (command.size() > 0)) {
                    fprintf(stdout, "%s: Command '%s%s%s', (t = %d ms)\n", __func__, "\033[1m", command.c_str(), "\033[0m", (int) t_ms);
                    std::ifstream wavFile("input.wav", std::ios::binary );
                    std::stringstream buffer;
                    buffer << wavFile.rdbuf();
                    httplib::Client cli("http://" + params.rag_url);
                    httplib::MultipartFormDataItems items{
                        { "file", buffer.str(), "", "application/octet-stream" },
                    };
                    cli.Post("/voice_input", items);
                }

                fprintf(stdout, "\n");

                audio.clear();
            }
        }
    }

    return 0;
}

int main(int argc, char ** argv) {
    whisper_params params;

    if (whisper_params_parse(argc, argv, params) == false) {
        return 1;
    }

    if (whisper_lang_id(params.language.c_str()) == -1) {
        fprintf(stderr, "error: unknown language '%s'\n", params.language.c_str());
        whisper_print_usage(argc, argv, params);
        exit(0);
    }

    // whisper init

    struct whisper_context_params cparams = whisper_context_default_params();
    cparams.use_gpu = params.use_gpu;

    struct whisper_context * ctx = whisper_init_from_file_with_params(params.model.c_str(), cparams);

    // print some info about the processing
    {
        fprintf(stderr, "\n");
        if (!whisper_is_multilingual(ctx)) {
            if (params.language != "en" || params.translate) {
                params.language = "en";
                params.translate = false;
                fprintf(stderr, "%s: WARNING: model is not multilingual, ignoring language and translation options\n", __func__);
            }
        }
        fprintf(stderr, "%s: processing, %d threads, lang = %s, task = %s, timestamps = %d ...\n",
                __func__,
                params.n_threads,
                params.language.c_str(),
                params.translate ? "translate" : "transcribe",
                params.no_timestamps ? 0 : 1);

        fprintf(stderr, "\n");
    }

    // init audio

    audio_async audio(30*1000);
    if (!audio.init(params.capture_id, WHISPER_SAMPLE_RATE)) {
        fprintf(stderr, "%s: audio.init() failed!\n", __func__);
        return 1;
    }

    audio.resume();

    // wait for 1 second to avoid any buffered noise
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    audio.clear();

    int ret_val = 0;

    if (ret_val == 0) {
        if (!params.prompt.empty()) {
            ret_val = always_prompt_transcription(ctx, audio, params);
        } else {
            fprintf(stderr, "prompt not found!\n");
            return 1;
        }
    }

    audio.pause();

    whisper_print_timings(ctx);
    whisper_free(ctx);

    return ret_val;
}
