"""Autonomous Research Paper Scout for ArXiv feeds."""

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

from src.autolearn.schemas import PaperScoutResult

DEFAULT_TARGET_KEYWORDS = [
    "context compression",
    "kv cache",
    "prompt pruning",
    "mcp security",
    "jailbreak",
    "agent memory",
]


class PaperScout:
    """Scouts recent research papers matching target optimization and security keywords."""

    TARGET_KEYWORDS = DEFAULT_TARGET_KEYWORDS

    def __init__(self, target_keywords: list[str] | None = None) -> None:
        self.target_keywords = (
            [k.lower().strip() for k in target_keywords]
            if target_keywords is not None
            else [k.lower().strip() for k in self.TARGET_KEYWORDS]
        )

    def _fetch_arxiv_feed(self, query: str, max_results: int = 20) -> str:
        """Fetch raw XML feed from arXiv API."""
        encoded_query = urllib.parse.quote(query)
        url = (
            f"http://export.arxiv.org/api/query?search_query={encoded_query}"
            f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "AegisPaperScout/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")

    def _compute_relevance_and_keywords(
        self, text: str
    ) -> tuple[float, list[str]]:
        """Compute matching keywords and relevance score based on keyword match density."""
        lower_text = text.lower()
        matched = [kw for kw in self.target_keywords if re.search(r"\b" + re.escape(kw) + r"\b", lower_text)]
        if not matched:
            return 0.0, []
        # Score bounded between 0.0 and 1.0 based on fraction of target keywords matched
        score = min(1.0, len(matched) / max(1, len(self.target_keywords)))
        # Boost score slightly if multiple occurrences exist
        total_occurrences = sum(len(re.findall(r"\b" + re.escape(kw) + r"\b", lower_text)) for kw in matched)
        density_bonus = min(0.2, (total_occurrences - len(matched)) * 0.05)
        final_score = min(1.0, round(score * 0.8 + 0.2 + density_bonus, 2))
        return final_score, matched

    def filter_papers(self, papers: list[dict[str, str]]) -> list[PaperScoutResult]:
        """Filter list of raw paper dictionaries based on target keywords."""
        results: list[PaperScoutResult] = []
        for p in papers:
            title = p.get("title", "")
            abstract = p.get("abstract", "") or p.get("summary", "")
            combined = f"{title}\n{abstract}"
            score, matched_kws = self._compute_relevance_and_keywords(combined)
            if matched_kws:
                paper_id = p.get("paper_id") or p.get("id", "")
                # Extract arxiv id if url
                if "/" in paper_id:
                    paper_id = paper_id.split("/")[-1]
                pub_date_raw = p.get("published_date") or p.get("published")
                pub_date = datetime.now(UTC)
                if pub_date_raw:
                    try:
                        pub_date = datetime.fromisoformat(pub_date_raw.replace("Z", "+00:00"))
                    except Exception:
                        pass
                authors_raw = p.get("authors")
                authors: list[str] = []
                if isinstance(authors_raw, list):
                    authors = authors_raw
                elif isinstance(authors_raw, str):
                    authors = [a.strip() for a in authors_raw.split(",")]

                url = p.get("url") or p.get("arxiv_url") or p.get("link")
                results.append(
                    PaperScoutResult(
                        paper_id=paper_id,
                        title=title.strip(),
                        authors=authors,
                        abstract=abstract.strip(),
                        keywords=matched_kws,
                        published_date=pub_date,
                        arxiv_url=url,
                        pdf_url=p.get("pdf_url"),
                        url=url,
                        relevance_score=score,
                    )
                )

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results

    async def scout_recent_papers(self, max_results: int = 10) -> list[PaperScoutResult]:
        """Fetch and scout recent papers matching keywords from arXiv Atom feed."""
        query = " OR ".join(f'all:"{kw}"' for kw in self.target_keywords[:5])
        xml_data = self._fetch_arxiv_feed(query=query, max_results=max_results)
        return self._parse_atom_feed(xml_data)

    def _parse_atom_feed(self, xml_data: str) -> list[PaperScoutResult]:
        """Parse Atom feed XML and filter for matching keywords."""
        root = ET.fromstring(xml_data)
        # Atom namespace
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        raw_papers: list[dict[str, Any]] = []

        for entry in root.findall("atom:entry", ns):
            id_elem = entry.find("atom:id", ns)
            title_elem = entry.find("atom:title", ns)
            summary_elem = entry.find("atom:summary", ns)
            published_elem = entry.find("atom:published", ns)

            raw_id = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            title = " ".join(title.split())
            summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
            summary = " ".join(summary.split())
            pub_date = published_elem.text.strip() if published_elem is not None and published_elem.text else ""

            authors = []
            for author in entry.findall("atom:author", ns):
                name_elem = author.find("atom:name", ns)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            link_elem = entry.find("atom:link[@rel='alternate']", ns)
            link = link_elem.attrib.get("href") if link_elem is not None else raw_id

            pdf_link_elem = entry.find("atom:link[@title='pdf']", ns)
            pdf_url = pdf_link_elem.attrib.get("href") if pdf_link_elem is not None else None

            raw_papers.append({
                "id": raw_id,
                "title": title,
                "summary": summary,
                "abstract": summary,
                "published": pub_date,
                "authors": authors,
                "url": link,
                "pdf_url": pdf_url,
            })

        return self.filter_papers(raw_papers)


__all__ = [
    "DEFAULT_TARGET_KEYWORDS",
    "PaperScout",
]
