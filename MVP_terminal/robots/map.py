#!/usr/bin/env python
"""
Simple ASCII map simulator for ESTER-Grid.
Polls dispatcher `/robots` to obtain last known robot states and draws
a crude grid using `pos` coordinates.

Usage:
  python map.py --server http://127.0.0.1:3000 --interval 0.5

This script expects dispatcher to expose `/robots` (returns registry with
`last_state.pos` when available). It will print a table and an ASCII map.
"""
import requests
import time
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('--server', default='http://127.0.0.1:3000')
parser.add_argument('--interval', type=float, default=0.5)
parser.add_argument('--width', type=int, default=40)
parser.add_argument('--height', type=int, default=20)
args = parser.parse_args()

SERVER = args.server
INTERVAL = args.interval
W = args.width
H = args.height

CLEAR = lambda: os.system('cls' if os.name == 'nt' else 'clear')


def fetch_robots():
    try:
        # Query `/robots` (connected robots only by default)
        r = requests.get(f"{SERVER}/robots", timeout=1.0)
        return r.json()
    except Exception as e:
        return {}


def compute_bounds(robots):
    xs = []
    ys = []
    for r, info in robots.items():
        st = info.get('last_state')
        if st and isinstance(st.get('pos'), (list, tuple)) and len(st['pos']) >= 2:
            x = float(st['pos'][0])
            y = float(st['pos'][-1])
            xs.append(x); ys.append(y)
    if not xs:
        return (-5, 5), (-5, 5)
    return (min(xs)-1, max(xs)+1), (min(ys)-1, max(ys)+1)


def draw_map(robots):
    # Only consider robots that have reported state (connected)
    active = {k: v for k, v in robots.items() if v.get('last_state')}

    (xmin, xmax), (ymin, ymax) = compute_bounds(active)
    # map coordinates to grid
    grid = [['.' for _ in range(W)] for _ in range(H)]

    table_lines = []
    for r, info in active.items():
        st = info.get('last_state')
        pos = None
        if st and isinstance(st.get('pos'), (list, tuple)) and len(st['pos']) >= 2:
            x = float(st['pos'][0])
            y = float(st['pos'][-1])
            # normalize
            gx = int((x - xmin) / (xmax - xmin + 1e-6) * (W-1))
            gy = int((y - ymin) / (ymax - ymin + 1e-6) * (H-1))
            # invert y for display
            gy = H - 1 - gy
            if 0 <= gy < H and 0 <= gx < W:
                label = r[:2]
                grid[gy][gx] = label[0]
            pos = (x, y)
        table_lines.append((r, info.get('port'), info.get('address'), pos))

    CLEAR()
    print("ESTER-Grid Map (ASCII)\n")
    if not table_lines:
        print("(No robots connected)")
        print('\nRobots: none')
        return

    for row in grid:
        print(''.join(cell if isinstance(cell, str) else '.' for cell in row))
    print('\nRobots:')
    print(f"{'id':<10} {'port':<6} {'addr':<15} pos")
    for r, port, addr, pos in table_lines:
        print(f"{r:<10} {str(port):<6} {str(addr):<15} {str(pos)}")


def main():
    while True:
        robots = fetch_robots()
        draw_map(robots)
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
