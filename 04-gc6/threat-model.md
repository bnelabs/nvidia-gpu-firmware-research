# GC6 trust-boundary analysis — static hypothesis
Scope: versioned public host-driver source and existing firmware artifacts. No suspend,
resume, GC6 trigger, register access or hardware validation is authorized.

The cited host resume path distinguishes normal boot and GC6 restoration, and source
comments describe reuse of protected state. The expected boundary is that trusted state
remains protected while a full verification step is skipped. That is a design assumption
to trace, not proof that every relevant register, DMA path or resume input is safe.

Separate the actor invoking a host-kernel function from the actor able to cause a normal
OS resume. Source-level call-site searches alone cannot exclude all user/guest influence.
Host-kernel compromise and GPU firmware compromise are also different security boundaries.

Retain exact source paths/commits, mode guards, protected-memory configuration and firmware
consumer evidence. State unknowns about per-field ACLs, retention and reset behavior.
Current disposition: no demonstrated exploit in this repository; no universal absence-of-
vulnerability or persistence claim. Continue offline analysis without probing the GPU.
