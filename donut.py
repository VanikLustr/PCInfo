#!/usr/bin/env python3
"""Spinning ASCII donut — a Python port of Andy Sloane's donut.c."""

import math
import os
import sys
import time

WIDTH, HEIGHT = 80, 24
SHADES = ".,-~:;=!*#$@"

# The torus is always sampled on the same grid, so cache the trigonometry.
THETAS = [(math.cos(j * 0.07), math.sin(j * 0.07)) for j in range(90)]
PHIS = [(math.cos(i * 0.02), math.sin(i * 0.02)) for i in range(314)]


def render(A, B):
    """Render one frame of the torus: a list of HEIGHT strings of WIDTH chars."""
    cosA, sinA = math.cos(A), math.sin(A)
    cosB, sinB = math.cos(B), math.sin(B)
    size = WIDTH * HEIGHT
    zbuf = [0.0] * size
    buf = [" "] * size

    for cosj, sinj in THETAS:
        h = cosj + 2.0
        for cosi, sini in PHIS:
            D = 1.0 / (sini * h * sinA + sinj * cosA + 5.0)
            t = sini * h * cosA - sinj * sinA
            x = int(WIDTH / 2 + 30.0 * D * (cosi * h * cosB - t * sinB))
            y = int(HEIGHT / 2 + 15.0 * D * (cosi * h * sinB + t * cosB))
            if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
                continue
            o = x + y * WIDTH
            if D <= zbuf[o]:
                continue
            zbuf[o] = D
            # Surface normal dotted with the light direction → brightness.
            N = int(8 * (
                (sinj * sinA - sini * cosj * cosA) * cosB
                - sini * cosj * sinA - sinj * cosA - cosi * cosj * sinB
            ))
            buf[o] = SHADES[max(0, min(N, len(SHADES) - 1))]

    return ["".join(buf[y * WIDTH:(y + 1) * WIDTH]) for y in range(HEIGHT)]


def main():
    if sys.platform == "win32":
        os.system("")  # enable ANSI escape codes in the Windows console

    out = sys.stdout
    out.write("\x1b[2J\x1b[?25l")  # clear screen, hide cursor
    out.flush()

    A = B = 0.0
    frame_time = 1.0 / 30.0

    try:
        while True:
            started = time.perf_counter()

            out.write("\x1b[H")  # cursor home
            out.write("\n".join(render(A, B)))
            out.flush()

            A += 0.04
            B += 0.02

            elapsed = time.perf_counter() - started
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        out.write("\x1b[?25h\n")  # show cursor again
        out.flush()


if __name__ == "__main__":
    main()
