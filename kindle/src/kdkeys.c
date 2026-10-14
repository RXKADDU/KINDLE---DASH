/* kdkeys: wait for one button press on the Kindle 4.
 * Usage: kdkeys SECONDS
 * Prints the key code of the first button pressed, or "timeout".
 */
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <sys/select.h>
#include <sys/time.h>
#include <linux/input.h>

int main(int argc, char **argv) {
    int fds[16], n = 0, maxfd = -1;
    long secs = argc > 1 ? atol(argv[1]) : 3600;
    char path[64];
    for (int i = 0; i < 16; i++) {
        snprintf(path, sizeof path, "/dev/input/event%d", i);
        int fd = open(path, O_RDONLY | O_NONBLOCK);
        if (fd >= 0) { fds[n++] = fd; if (fd > maxfd) maxfd = fd; }
    }
    if (n == 0) { puts("noinput"); return 1; }

    struct timeval end, now;
    gettimeofday(&end, NULL);
    end.tv_sec += secs;

    for (;;) {
        gettimeofday(&now, NULL);
        long left = (end.tv_sec - now.tv_sec) * 1000000L + (end.tv_usec - now.tv_usec);
        if (left <= 0) { puts("timeout"); return 0; }
        struct timeval tv = { left / 1000000L, left % 1000000L };
        fd_set set; FD_ZERO(&set);
        for (int i = 0; i < n; i++) FD_SET(fds[i], &set);
        int r = select(maxfd + 1, &set, NULL, NULL, &tv);
        if (r < 0) continue;
        if (r == 0) { puts("timeout"); return 0; }
        for (int i = 0; i < n; i++) {
            if (!FD_ISSET(fds[i], &set)) continue;
            struct input_event ev;
            while (read(fds[i], &ev, sizeof ev) == (ssize_t)sizeof ev) {
                if (ev.type == EV_KEY && ev.value == 1) {
                    printf("%d\n", ev.code);
                    fflush(stdout);
                    return 0;
                }
            }
        }
    }
}
