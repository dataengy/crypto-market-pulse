import json
from pathlib import Path
import pytest

beam = pytest.importorskip("apache_beam")
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.test_stream import TestStream
from apache_beam.testing.util import assert_that, equal_to
from apache_beam.transforms.window import TimestampedValue
from market_pulse.beam_pipeline import build_windowed

FIXTURE = Path(__file__).parent / "fixtures/trades.jsonl"


def test_beam_event_time_window_replay():
    events = [json.loads(line) for line in FIXTURE.read_text().splitlines()]
    # Synthetic test stream: test out-of-order arrivals plus duplicate within window.
    start = events[0]["event_time_ms"] // 1000
    stream = (TestStream()
              .advance_watermark_to(start - 2)
              .add_elements([TimestampedValue(e, e["event_time_ms"] / 1000) for e in events])
              .advance_watermark_to_infinity())
    with TestPipeline(options=beam.options.pipeline_options.PipelineOptions(streaming=True)) as pipeline:
        output = pipeline | "ReplayTrades" >> stream | "OHLCV" >> build_windowed()
        counts = output | "Summarize" >> beam.Map(lambda e: (e["symbol"], e["trade_count"], e["window_start_ms"]))
        minute = events[0]["event_time_ms"] // 60000 * 60000
        assert_that(counts, equal_to([
            ("BTCUSDT", 4, minute), ("ETHUSDT", 1, minute),
            ("BTCUSDT", 1, minute + 60000), ("ETHUSDT", 1, minute + 60000)
        ]))
