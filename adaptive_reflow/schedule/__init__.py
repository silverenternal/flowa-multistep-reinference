"""Adaptive reflow — outer restart-noise budget (DTB-NA1).

Closed cosine / linear / constant schedule family + stateful sampler.
"""
from .cosine import (
    ERR_CONFIG_HASH_EMPTY,
    ERR_CYCLE_LENGTH_NON_INT,
    ERR_CYCLE_LENGTH_TOO_SMALL,
    ERR_DELTA_CAP_INVALID,
    ERR_FRESH_NOISE_FLOOR_INVALID,
    ERR_N_MAX_LT_N_MIN,
    ERR_N_MAX_NOT_FINITE,
    ERR_N_MAX_OUT_OF_RANGE,
    ERR_N_MIN_NOT_FINITE,
    ERR_N_MIN_OUT_OF_RANGE,
    ERR_NOT_FROZEN_BEFORE_EVAL,
    ERR_PER_CHANNEL_CAP_INVALID,
    ERR_RESTART_TRIGGER_INVALID,
    ERR_SCHEDULE_FAMILY_INVALID,
    ERR_UNKNOWN_CHANNEL,
    CosineScheduleSampler,
    build_fresh_noise_diagnostics,
    default_floor_by_channel,
    memory_fraction_from_schedule,
    n_cap_for_round,
    validate_cosine_schedule_config,
)
