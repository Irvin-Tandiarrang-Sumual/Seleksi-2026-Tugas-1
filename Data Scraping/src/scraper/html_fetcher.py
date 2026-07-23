import os
import random
import re
import time
import urllib.parse

import requests


class HTMLFetcher:
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    ]

    def __init__(self):
        self.session = requests.Session()

    def get_url_candidates(self, url: str) -> list[str]:
        """Generate alternative candidate URLs to try in case of 404 (due to typos on server or HTML)."""
        candidates = []
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        decoded_path = urllib.parse.unquote(path)

        fixed_path = decoded_path
        if "(" in fixed_path and ")" not in fixed_path.split("/")[-1]:
            base, ext = os.path.splitext(fixed_path)
            last_segment = base.split("/")[-1]
            if "(" in last_segment and ")" not in last_segment:
                fixed_path = base + ")" + ext

        segments = fixed_path.split("/")
        filename = segments[-1]
        filename = re.sub(r"\(\s*([^)]+?)\s*\)", r"(\1)", filename)
        filename = re.sub(r"\s+\.pdf$", ".pdf", filename)
        segments[-1] = filename
        fixed_path = "/".join(segments)

        path_variations = [fixed_path]
        for i, segment in enumerate(segments):
            if re.match(r"^Makalah\d{4}$", segment, re.IGNORECASE):
                new_segments = list(segments)
                new_segments[i] = "Makalah"
                path_variations.append("/".join(new_segments))
            elif segment.lower() == "makalah":
                year = None
                for other_segment in segments:
                    year_match = re.search(r"20\d{2}", other_segment)
                    if year_match:
                        year = year_match.group(0)
                        range_match = re.search(
                            r"20(\d{2})[-/]20(\d{2})", other_segment
                        )
                        if range_match:
                            year = "20" + range_match.group(2)
                        break
                if year:
                    new_segments = list(segments)
                    new_segments[i] = f"Makalah{year}"
                    path_variations.append("/".join(new_segments))
                    new_segments[i] = f"makalah{year}"
                    path_variations.append("/".join(new_segments))

        if decoded_path not in path_variations:
            path_variations.append(decoded_path)

        for p_var in path_variations:
            quoted_p = urllib.parse.quote(p_var, safe="/~")
            new_url = urllib.parse.urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    quoted_p,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )
            if new_url != url and new_url not in candidates:
                candidates.append(new_url)

        return candidates

    def fetch(
        self, url: str, return_final_url: bool = False
    ) -> bytes | tuple[bytes, str] | None:
        if not url:
            return None

        parsed = urllib.parse.urlparse(url)
        quoted_path = urllib.parse.quote(parsed.path, safe="/~")
        quoted_query = urllib.parse.quote(parsed.query, safe="=&")
        url = urllib.parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                quoted_path,
                parsed.params,
                quoted_query,
                parsed.fragment,
            )
        )

        time.sleep(random.uniform(0.5, 1.5))

        headers = {
            "User-Agent": random.choice(self.user_agents),
        }

        retries = 3
        backoff = 1.0
        content = None
        final_url = url
        is_404 = False

        for attempt in range(retries + 1):
            try:
                response = self.session.get(url, timeout=10, headers=headers)
                response.raise_for_status()
                content = response.content
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    is_404 = True
                    break
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < retries:
                        sleep_time = backoff * (2**attempt) + random.uniform(0.1, 0.5)
                        print(
                            f"[Retry] Server error/rate limit ({e.response.status_code}) fetching {url}. Retrying in {sleep_time:.2f}s..."
                        )
                        time.sleep(sleep_time)
                        continue
                print(f"HTTP Error fetching {url}: {e}")
                break
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                if attempt < retries:
                    sleep_time = backoff * (2**attempt) + random.uniform(0.1, 0.5)
                    print(
                        f"[Retry] Connection error/timeout fetching {url}. Retrying in {sleep_time:.2f}s..."
                    )
                    time.sleep(sleep_time)
                    continue
                print(f"Connection error/timeout fetching {url}: {e}")
                break
            except requests.RequestException as e:
                print(f"Request exception fetching {url}: {e}")
                break

        if is_404:
            candidates = self.get_url_candidates(url)
            for cand in candidates:
                time.sleep(random.uniform(0.5, 1.5))
                headers = {"User-Agent": random.choice(self.user_agents)}
                for attempt in range(retries + 1):
                    try:
                        response = self.session.get(cand, timeout=10, headers=headers)
                        response.raise_for_status()
                        content = response.content
                        final_url = cand
                        print(
                            f"[Auto-Correct] Successfully fetched {cand} instead of original {url}"
                        )
                        break
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 404:
                            break
                        if e.response.status_code in [429, 500, 502, 503, 504]:
                            if attempt < retries:
                                sleep_time = backoff * (2**attempt) + random.uniform(
                                    0.1, 0.5
                                )
                                time.sleep(sleep_time)
                                continue
                        break
                    except (
                        requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout,
                    ):
                        if attempt < retries:
                            sleep_time = backoff * (2**attempt) + random.uniform(
                                0.1, 0.5
                            )
                            time.sleep(sleep_time)
                            continue
                        break
                    except requests.RequestException:
                        break
                if content is not None:
                    break

        if content is None:
            print(
                f"Error fetching {url}: 404 Client Error: Not Found"
                if is_404
                else f"Error fetching {url}"
            )
            return None

        if return_final_url:
            return content, final_url
        return content
