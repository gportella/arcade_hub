#!/usr/bin/env python
"""Command-line helpers for interacting with the Connect 4 API."""

from __future__ import annotations

import argparse
import json
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _request(method: str, path: str, *, base_url: str, **kwargs: Any) -> httpx.Response:
    with httpx.Client(base_url=base_url, timeout=5.0) as client:
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        return response


def healthcheck(args: argparse.Namespace) -> None:
    response = _request("GET", "/health", base_url=args.base_url)
    _print_json(response.json())


def create_game(args: argparse.Namespace) -> None:
    payload: dict[str, Any] = {}
    if args.game_id:
        payload["gameId"] = args.game_id
    if args.mode:
        payload["mode"] = args.mode
    response = _request("POST", "/games", base_url=args.base_url, json=payload)
    _print_json(response.json())


def list_games(args: argparse.Namespace) -> None:
    response = _request("GET", "/games", base_url=args.base_url)
    _print_json(response.json())


def get_game(args: argparse.Namespace) -> None:
    response = _request("GET", f"/games/{args.game_id}", base_url=args.base_url)
    _print_json(response.json())


def print_board(args: argparse.Namespace) -> None:
    response = _request(
        "GET", f"/games/{args.game_id}/board_state", base_url=args.base_url
    )
    for row in response.json()[-1::-1]:
        print("  ".join(row))
    # _print_json(response.json())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interact with the Connect 4 backend API"
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="Base URL of the API"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    health_parser = subparsers.add_parser("health", help="Run the healthcheck endpoint")
    health_parser.set_defaults(func=healthcheck)

    list_parser = subparsers.add_parser(
        "list", help="List currently active game sessions"
    )
    list_parser.set_defaults(func=list_games)

    create_parser = subparsers.add_parser("create", help="Register a new game session")
    create_parser.add_argument(
        "--game-id", help="Explicit game identifier to use (optional)"
    )
    create_parser.add_argument(
        "--mode",
        choices=["solo", "multiplayer"],
        help="Game mode (default: multiplayer)",
    )
    create_parser.set_defaults(func=create_game)

    get_parser = subparsers.add_parser("get", help="Inspect a specific game session")
    get_parser.add_argument("game_id", help="Identifier of the session to fetch")
    # get_parser.set_defaults(func=get_game)
    get_parser.set_defaults(func=print_board)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "func")
    handler(args)


if __name__ == "__main__":
    main()
