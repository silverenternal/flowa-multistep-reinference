# FlowA Component

This repository owns one source-level FlowA component. It is mounted by
`flowa-denovo-core` at its original package path through a pinned Git
submodule, so it preserves the existing Python import, model-state, and
checkpoint ABI.

Do not commit datasets, checkpoints, experiment artifacts, compiled objects,
or historical status/todo records. Change this component here, run its focused
contract tests from a checkout of the parent mainline, then update the parent
submodule pin deliberately.
