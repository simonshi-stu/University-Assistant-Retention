from course_retention import acquisition
from course_retention.acquisition import CacheAdapter, fetch_url, ingest_subject


def test_cache_hit_requires_no_network(tmp_path, monkeypatch):
    cache = CacheAdapter(tmp_path)
    url = "https://courses.illinois.edu/cisapp/explorer/schedule/2023/fall/CS.xml"
    cache.put(url, b"<subject id='CS'><courses/></subject>")

    def fail(*args, **kwargs):
        raise AssertionError("network must not be used on cache hit")

    monkeypatch.setattr(acquisition, "_http_get", fail)
    result = fetch_url(url, cache, allow_live=True)
    assert result.status == "cache"
    assert result.content.startswith(b"<subject")


def test_offline_cache_miss_is_blocked_not_fetched(tmp_path, monkeypatch):
    cache = CacheAdapter(tmp_path)

    def fail(*args, **kwargs):
        raise AssertionError("network must not be used in offline mode")

    monkeypatch.setattr(acquisition, "_http_get", fail)
    result = fetch_url("https://example.invalid/missing.xml", cache, allow_live=False)
    assert result.status == "blocked"
    assert "cache miss" in result.error


def test_ingest_subject_uses_cache_without_network(tmp_path, monkeypatch):
    cache = CacheAdapter(tmp_path)
    subject_url = "https://courses.illinois.edu/cisapp/explorer/schedule/2023/fall/CS.xml"
    course_url = "https://courses.illinois.edu/cisapp/explorer/schedule/2023/fall/CS/101.xml"
    cache.put(
        subject_url,
        f"<subject id='CS'><courses><course id='CS 101' href='{course_url}'/></courses></subject>".encode(),
    )
    cache.put(
        course_url,
        b"<course id='CS 101'><name>CS 101</name><title>Intro</title><sections/></course>",
    )

    def fail(*args, **kwargs):
        raise AssertionError("network must not be used")

    monkeypatch.setattr(acquisition, "_http_get", fail)
    records, parsed = ingest_subject("2023-fall", "CS", cache, allow_live=True)
    assert len(records) == 2
    assert all(record.status == "cache" for record in records)
    assert parsed[0].course.subject == "CS"


