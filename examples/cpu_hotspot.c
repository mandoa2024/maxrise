#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

static volatile double sink;

__attribute__((noinline)) static void parse_payload(uint64_t rounds) {
    double value = 0.0;
    for (uint64_t i = 1; i < rounds; ++i) {
        value += sqrt((double)i) * 0.000001;
    }
    sink = value;
}

__attribute__((noinline)) static void serialize_response(uint64_t rounds) {
    uint64_t hash = 1469598103934665603ULL;
    for (uint64_t i = 0; i < rounds; ++i) {
        hash = (hash ^ i) * 1099511628211ULL;
    }
    sink = (double)hash;
}

__attribute__((noinline)) static void handle_request(void) {
    parse_payload(5000000);
    serialize_response(1800000);
}

int main(void) {
    fprintf(stderr, "cpu_hotspot pid=%d\n", getpid());
    while (1) {
        handle_request();
    }
}
