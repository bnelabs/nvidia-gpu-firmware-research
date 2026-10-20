# Monitoring collector — corrected default and scope
This entry point delegates to scripts/capture_state.py. No ctypes bindings, library loading,
polling loop, automatic log scraping, root, tracing or experimental fallback remains.
Default invocation and --dry-run print a plan without contacting a GPU.
--dry-run combined with --live is refused. Legacy --interval/--duration/--out options are
refused; the fixed collector accepts only an explicit live UUID request and optional new
JSON capture path. Do not install it as a service or autostart it.

The original collector is preserved as historical source in the archive and Git history.
Its dry-run actually initialized NVML and sampled hardware; many getters discarded failure
status and could report zero as a reading. Device index 0 was mixed with procfs information
from all GPUs. A reported ctypes crash did not prove a bad vendor ABI. No old safe/zero-risk
or negligible-RPC-overhead assertion is retained.

Read [CONSTITUTION.md](../../CONSTITUTION.md). Standard vendor telemetry still invokes the
driver; use retained files only when hardware contact is not acceptable. There is no proof
that the external worker has adopted these instructions merely because the files changed.
