"""Explicit local retention maintenance; does not erase receipt audit history."""
import argparse
import json

from receiving.config import Settings
from receiving.photos import purge_expired
from receiving.workflow import Workflow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["purge-expired-photos"])
    parser.parse_args()
    print(json.dumps(purge_expired(Workflow(Settings.from_env())), indent=2))


if __name__ == "__main__":
    main()
