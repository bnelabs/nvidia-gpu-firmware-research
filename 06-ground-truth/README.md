# Historical ground truth
These captures are preserved unchanged. They describe earlier snapshots, not current GPU
health or proof that a worker never disturbed inference. Use offline analysis only.

Record each file's SHA-256 and size when using it. The filenames configspace-4k are
historical labels: the old script invoked the conventional -xxx dump, not extended -xxxx.
Do not repeat those reads. Some tracer exports may be fixed 384-byte prefixes despite
larger declared payloads; verify actual retained lengths before claiming completeness.

Manually transcribed fixture JSON is not a complete raw capture or independent source.
No new root capture, custom RM probe, tracing or firmware acquisition from the GPU is
authorized. The current collector's default prints a plan without hardware contact.
