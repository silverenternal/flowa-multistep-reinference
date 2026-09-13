# Wave 128 CIFAR checkpoint-loader fix

The loader now accepts raw tensor state dicts and explicit training bundles
under `ema` or `model` (EMA takes precedence), while rejecting unsupported or
empty nested structures. Existing raw state-dict behavior is unchanged.

CPU focused checks exercised raw, model bundle, EMA precedence, and invalid
payload rejection. Existing synthetic adapter smoke remains passing. No
long-running inference or GPU sweep was started.
