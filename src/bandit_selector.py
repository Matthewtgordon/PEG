# Bandit-based macro selector with persistence and exploration bonuses.
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List


class BanditSelector:
    """Thompson Sampling bandit with weight persistence."""

    def __init__(self, weights_path: Path | str = Path("bandit_weights.json"), decay: float = 0.9):
        self.weights_path = Path(weights_path)
        self.decay = decay
        self.weights: Dict[str, Dict[str, float]] = self._load()
        self.metrics: Dict[str, Any] = {"selections": 0}

    def _load(self) -> Dict[str, Dict[str, float]]:
        if self.weights_path.exists():
            with self.weights_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self) -> None:
        with self.weights_path.open("w", encoding="utf-8") as f:
            json.dump(self.weights, f)

    def choose(self, macros: List[str], history: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        if history:
            for stats in self.weights.values():
                stats['successes'] *= self.decay
                stats['failures'] *= self.decay
                stats['plays'] = stats.get('plays', 0) * self.decay
                stats['total_reward'] = stats.get('total_reward', 0) * self.decay

        pass_threshold = config.get('ci', {}).get('minimum_score', 0.8)
        for macro in macros:
            self.weights.setdefault(macro, {'successes': 1, 'failures': 1, 'plays': 0, 'total_reward': 0})

        for record in history:
            macro = record.get('macro')
            if not macro:
                continue
            if 'reward' in record:
                reward = record['reward']
            else:
                reward = 1 if record.get('score', 0) >= pass_threshold else 0
            stats = self.weights.setdefault(macro, {'successes': 1, 'failures': 1, 'plays': 0, 'total_reward': 0})
            if reward:
                stats['successes'] += 1
            else:
                stats['failures'] += 1
            stats['plays'] += 1
            stats['total_reward'] += reward

        best_macro = None
        best_sample = -1.0
        for macro in macros:
            stats = self.weights[macro]
            sample = random.betavariate(stats['successes'], stats['failures'])
            bonus = 1.0 / (1 + stats.get('plays', 0))
            sample += bonus
            if sample > best_sample:
                best_sample = sample
                best_macro = macro

        self.metrics['selections'] += 1
        self._save()

        if best_macro is None and macros:
            best_macro = macros[0]
        return best_macro


def choose_macro(macros: List[str], history: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    selector = BanditSelector()
    return selector.choose(macros, history, config)
