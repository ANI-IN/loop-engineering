"""The deck's source list, numbered as .dev/deck-sources.md numbers it, 26 October 2026.

Terms the titles use: Structured Query Language (SQL), large language model (LLM), and
application programming interface (API).

A source marker [^n] on a slide names entry n here; the outline builder refuses a marker past the
end of SOURCES. Each entry gives the source's full title, its authors or organisation, its year
("undated" when the page carries no date), and its full address, as deck-sources.md verified them.
The sources slides of the closing show each entry in a shorter form (the short title: a paper's own
name, such as "Spider 2.0", or a page's title cut at its colon), grouped by topic as deck-sources.md
groups them, with the long products group split into four panels so that each slide balances its
two columns. sources_slide(...) writes one slide's lines in the slide schema's grammar.
"""

from collections.abc import Iterable

GITHUB = "https://github.com/ANI-IN/loop-engineering/blob/main"

# The topics of deck-sources.md, in its order. Each source names its topic by key.
TOPICS = {
    "agent": "Agent design",
    "verification": "Verification and evaluation",
    "research": "Text-to-SQL research and benchmarks",
    "events": "Event-driven systems",
    "products": "Products and documentation",
    "course": "The course's own evidence, on GitHub",
}

# (number, topic, full title, short title for the slide, authors or organisation, year, address)
ENTRIES = [
    # Agent design
    (
        1,
        "agent",
        "The Art of Loop Engineering",
        "The Art of Loop Engineering",
        "Sydney Runkle, LangChain",
        "2026",
        "https://www.langchain.com/blog/the-art-of-loop-engineering",
    ),
    (
        2,
        "agent",
        "Loop Engineering: Design systems that prompt your agents",
        "Loop Engineering",
        "Cobus Greyling",
        "undated",
        "https://cobusgreyling.github.io/loop-engineering/",
    ),
    (
        3,
        "agent",
        "Building effective agents",
        "Building effective agents",
        "Erik Schluntz and Barry Zhang, Anthropic",
        "2024",
        "https://www.anthropic.com/engineering/building-effective-agents",
    ),
    (
        4,
        "agent",
        "Writing effective tools for AI agents",
        "Writing effective tools for AI agents",
        "Ken Aizawa, Anthropic",
        "2025",
        "https://www.anthropic.com/engineering/writing-tools-for-agents",
    ),
    (
        5,
        "agent",
        "Build a SQL agent",
        "Build a SQL agent",
        "LangChain",
        "undated",
        "https://docs.langchain.com/oss/python/langchain/sql-agent",
    ),
    (
        6,
        "agent",
        "Build a custom SQL agent (LangGraph)",
        "Build a custom SQL agent",
        "LangChain",
        "undated",
        "https://docs.langchain.com/oss/python/langgraph/sql-agent",
    ),
    (
        7,
        "agent",
        "Structured output",
        "Structured output",
        "LangChain",
        "undated",
        "https://docs.langchain.com/oss/python/langchain/structured-output",
    ),
    (
        8,
        "agent",
        "Custom middleware",
        "Custom middleware",
        "LangChain",
        "undated",
        "https://docs.langchain.com/oss/python/langchain/middleware/custom",
    ),
    (
        9,
        "agent",
        "Prebuilt middleware",
        "Prebuilt middleware",
        "LangChain",
        "undated",
        "https://docs.langchain.com/oss/python/langchain/middleware/built-in",
    ),
    (
        10,
        "agent",
        "Human-in-the-loop",
        "Human-in-the-loop",
        "LangChain",
        "undated",
        "https://docs.langchain.com/oss/python/langchain/human-in-the-loop",
    ),
    (
        11,
        "agent",
        "Temperature in GPT-5 models",
        "Temperature in GPT-5 models",
        "OpenAI Developer Community",
        "2025",
        "https://community.openai.com/t/temperature-in-gpt-5-models/1337133",
    ),
    # Verification and evaluation
    (
        12,
        "verification",
        "Semantic Evaluation for Text-to-SQL with Distilled Test Suites",
        "Semantic Evaluation for Text-to-SQL with Distilled Test Suites",
        "Ruiqi Zhong, Tao Yu, Dan Klein",
        "2020",
        "https://arxiv.org/abs/2010.02840",
    ),
    (
        13,
        "verification",
        "SQL Injection Prevention Cheat Sheet",
        "SQL Injection Prevention Cheat Sheet",
        "OWASP Cheat Sheet Series",
        "undated",
        "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
    ),
    (
        14,
        "verification",
        "Appendix A. PostgreSQL Error Codes",
        "PostgreSQL Error Codes",
        "PostgreSQL Global Development Group",
        "undated",
        "https://www.postgresql.org/docs/current/errcodes-appendix.html",
    ),
    (
        15,
        "verification",
        "ALTER ROLE",
        "ALTER ROLE",
        "PostgreSQL Global Development Group",
        "undated",
        "https://www.postgresql.org/docs/current/sql-alterrole.html",
    ),
    # Text-to-SQL research and benchmarks
    (
        16,
        "research",
        "Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database "
        "Grounded Text-to-SQLs (BIRD)",
        "BIRD",
        "Jinyang Li and others",
        "2023",
        "https://arxiv.org/abs/2305.03111",
    ),
    (
        17,
        "research",
        "Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows",
        "Spider 2.0",
        "Fangyu Lei and others",
        "2024",
        "https://arxiv.org/abs/2411.07763",
    ),
    (
        18,
        "research",
        "LinkAlign: Scalable Schema Linking for Real-World Large-Scale Multi-Database Text-to-SQL "
        "(version 3)",
        "LinkAlign",
        "Yihan Wang, Peiyu Liu",
        "2025",
        "https://arxiv.org/html/2503.18596v3",
    ),
    (
        19,
        "research",
        "MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL",
        "MAGIC",
        "Arian Askari, Christian Poelitz, Xinye Tang",
        "2024",
        "https://arxiv.org/abs/2406.12692",
    ),
    (
        20,
        "research",
        "Toward Real-World Table Agents: Capabilities, Workflows, and Design Principles for "
        "LLM-based Table Intelligence",
        "Toward Real-World Table Agents",
        "Jiaming Tian and others",
        "2025",
        "https://arxiv.org/html/2507.10281",
    ),
    (
        21,
        "research",
        "SEED: Enhancing Text-to-SQL Performance and Practical Usability Through Automatic Evidence "
        "Generation",
        "SEED",
        "Janghyeon Yun, Sang-goo Lee",
        "2025",
        "https://arxiv.org/abs/2506.07423",
    ),
    (
        22,
        "research",
        "AMBROSIA: A Benchmark for Parsing Ambiguous Questions into Database Queries",
        "AMBROSIA",
        "Irina Saparina, Mirella Lapata",
        "2024",
        "https://arxiv.org/abs/2406.19073",
    ),
    (
        23,
        "research",
        "PRACTIQ: A Practical Conversational Text-to-SQL dataset with Ambiguous and Unanswerable "
        "Queries",
        "PRACTIQ",
        "Mingwen Dong and others",
        "2024",
        "https://arxiv.org/abs/2410.11076v1",
    ),
    (
        24,
        "research",
        "DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction",
        "DIN-SQL",
        "Mohammadreza Pourreza, Davood Rafiei",
        "2023",
        "https://arxiv.org/abs/2304.11015",
    ),
    (
        25,
        "research",
        "ReFoRCE: A Text-to-SQL Agent with Self-Refinement, Consensus Enforcement, and Column "
        "Exploration",
        "ReFoRCE",
        "Minghang Deng and others",
        "2025",
        "https://arxiv.org/abs/2502.00675",
    ),
    # Event-driven systems
    (
        26,
        "events",
        "Postgres Job Queues & Failure By MVCC",
        "Postgres Job Queues",
        "Brandur Leach",
        "2015",
        "https://brandur.org/postgres-queues",
    ),
    (
        27,
        "events",
        "You Don't Need a Job Queue, Postgres Already Has SKIP LOCKED",
        "You Don't Need a Job Queue",
        "Nurul Sundarani, Prisma",
        "2026",
        "https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked",
    ),
    (
        28,
        "events",
        "SELECT",
        "SELECT",
        "PostgreSQL Global Development Group",
        "undated",
        "https://www.postgresql.org/docs/current/sql-select.html",
    ),
    (
        29,
        "events",
        "Making retries safe with idempotent APIs",
        "Making retries safe",
        "Malcolm Featonby, Amazon Web Services",
        "undated",
        "https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/",
    ),
    # Products and documentation
    (
        30,
        "products",
        "dbt Semantic Layer",
        "dbt Semantic Layer",
        "dbt Labs",
        "undated",
        "https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl",
    ),
    (
        31,
        "products",
        "About MetricFlow",
        "About MetricFlow",
        "dbt Labs",
        "undated",
        "https://docs.getdbt.com/docs/build/about-metricflow",
    ),
    (
        32,
        "products",
        "dbt Semantic Layer FAQs",
        "dbt Semantic Layer FAQs",
        "dbt Labs",
        "undated",
        "https://docs.getdbt.com/docs/use-dbt-semantic-layer/sl-faqs",
    ),
    (
        33,
        "products",
        "Introduction (Cube documentation)",
        "Introduction",
        "Cube Dev",
        "undated",
        "https://cube.dev/docs/product/introduction",
    ),
    (
        34,
        "products",
        "AI context (Cube documentation)",
        "AI context",
        "Cube Dev",
        "undated",
        "https://docs.cube.dev/docs/data-modeling/ai-context",
    ),
    (
        35,
        "products",
        "Analytics Chat (Cube documentation)",
        "Analytics Chat",
        "Cube Dev",
        "undated",
        "https://docs.cube.dev/docs/explore-analyze/analytics-chat",
    ),
    (
        36,
        "products",
        "Cortex Analyst",
        "Cortex Analyst",
        "Snowflake",
        "undated",
        "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst",
    ),
    (
        37,
        "products",
        "Overview of semantic views",
        "Semantic views",
        "Snowflake",
        "undated",
        "https://docs.snowflake.com/en/user-guide/views-semantic/overview",
    ),
    (
        38,
        "products",
        "Cortex Analyst Verified Query Repository",
        "Verified Query Repository",
        "Snowflake",
        "undated",
        "https://docs.snowflake.com/user-guide/snowflake-cortex/cortex-analyst/"
        "verified-query-repository",
    ),
    (
        39,
        "products",
        "Suggestions for semantic models and views",
        "Suggestions",
        "Snowflake",
        "undated",
        "https://docs.snowflake.com/en/user-guide/views-semantic/verified-query-suggestions",
    ),
    (
        40,
        "products",
        "Cortex Analyst evaluations",
        "Cortex Analyst evaluations",
        "Snowflake",
        "undated",
        "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst-evaluations",
    ),
    (
        41,
        "products",
        "Cortex Analyst administrator monitoring",
        "Administrator monitoring",
        "Snowflake",
        "undated",
        "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/"
        "admin-observability",
    ),
    (
        42,
        "products",
        "Genie",
        "Genie",
        "Databricks",
        "undated",
        "https://docs.databricks.com/aws/en/genie/",
    ),
    (
        43,
        "products",
        "Test and monitor a Genie Agent",
        "Test and monitor a Genie Agent",
        "Databricks",
        "2026",
        "https://docs.databricks.com/aws/en/genie-agents/monitor",
    ),
    (
        44,
        "products",
        "Curate an effective Genie Agent",
        "Curate an effective Genie Agent",
        "Databricks",
        "undated",
        "https://docs.databricks.com/aws/en/genie/best-practices",
    ),
    (
        45,
        "products",
        "How to Build Production-Ready Genie Spaces, and Build Trust Along the Way",
        "Production-Ready Genie Spaces",
        "Pulkit Pareek, Eric Lind, Databricks",
        "2026",
        "https://www.databricks.com/blog/how-build-production-ready-genie-spaces-and-build-trust-"
        "along-way",
    ),
    (
        46,
        "products",
        "Question-SQL Pairs",
        "Question-SQL Pairs",
        "Wren AI",
        "undated",
        "https://docs.getwren.ai/oss/guide/knowledge/question-sql-pairs",
    ),
    (
        47,
        "products",
        "Documentation (What is Vanna 2.0?)",
        "What is Vanna 2.0?",
        "Vanna AI",
        "undated",
        "https://vanna.ai/docs/",
    ),
    (
        48,
        "products",
        "Golden SQLs",
        "Golden SQLs",
        "Dataherald",
        "undated",
        "https://dataherald.readthedocs.io/en/latest/api.golden_sql.html",
    ),
    (
        49,
        "products",
        "QueryGPT: Natural Language to SQL Using Generative AI",
        "QueryGPT",
        "Jeffrey Johnson, Callie Busch, Abhi Khune, Pradeep Chakka, Uber",
        "2024",
        "https://www.uber.com/blog/query-gpt/",
    ),
    # The course's own evidence
    (
        50,
        "course",
        "Calibration report",
        "Calibration report",
        "ANI-IN, Loop Engineering",
        "2026",
        f"{GITHUB}/docs/calibration-report.md",
    ),
    (
        51,
        "course",
        "Benefits",
        "Benefits",
        "ANI-IN, Loop Engineering",
        "2026",
        f"{GITHUB}/docs/benefits.md",
    ),
    (
        52,
        "course",
        "Evidence",
        "Evidence",
        "ANI-IN, Loop Engineering",
        "2026",
        f"{GITHUB}/docs/evidence.md",
    ),
    (53, "course", "Costs", "Costs", "ANI-IN, Loop Engineering", "2026", f"{GITHUB}/docs/costs.md"),
    # Added 26 October 2026, after the list of deck-sources.md (verified the same day, it answered):
    # the SQLDatabase utility shows 3 sample rows by default (sample_rows_in_table_info=3), cuts
    # values at 300 characters (max_string_length=300), and run(fetch="all") returns every row.
    (
        54,
        "agent",
        "SQLDatabase utility, source code",
        "SQLDatabase utility",
        "LangChain (langchain-community)",
        "2026",
        "https://github.com/langchain-ai/langchain-community/blob/main/libs/community/"
        "langchain_community/utilities/sql_database.py",
    ),
]

assert [e[0] for e in ENTRIES] == list(range(1, len(ENTRIES) + 1)), "numbered 1 to N in order"

# The full entries, one per source, in number order: what the outline lists at its end and what the
# learner-facing sources page mirrors. SOURCES[n - 1] is source n.
SOURCES = [
    f"[{n}] {title}. {who}, {year}. {url}" for n, _topic, title, _short, who, year, url in ENTRIES
]


# On the slide, a few entries name the organisation alone, or the authors alone, so that each entry
# keeps to two lines at 14 points; the full entry above names both.
SLIDE_WHO = {
    1: "Sydney Runkle",
    3: "Anthropic",
    4: "Ken Aizawa",
    11: "OpenAI community",
    12: "Ruiqi Zhong and others",
    13: "Open Worldwide Application Security Project (OWASP)",
    14: "PostgreSQL",
    15: "PostgreSQL",
    28: "PostgreSQL",
    29: "Amazon Web Services",
    45: "Databricks",
    49: "Uber",
    50: "Loop Engineering",
    51: "Loop Engineering",
    52: "Loop Engineering",
    53: "Loop Engineering",
    54: "LangChain",
}


def entry_line(n: int) -> str:
    """One entry as the sources slide shows it: '[n] Short title, authors, year, address'. A page
    that carries no date shows no year on the slide (the full entry says "undated"), so that the
    three sources slides keep each entry to one line where the address allows."""
    _n, _topic, _title, short, who, year, url = ENTRIES[n - 1]
    when = "" if year == "undated" else f" {year},"
    return f"[{n}] {short}, {SLIDE_WHO.get(n, who)},{when} {url}"


def sources_slide(*panels: tuple[str, Iterable[int]]) -> list[str]:
    """A sources slide's lines: for each panel, its 'Group:' heading, then its entries by number.
    The deck builder splits a sources slide into two columns at a group heading. The slides list
    only the sources the deck cites; the course's sources page lists every verified source."""
    lines = []
    for heading, numbers in panels:
        lines.append(f"Group: {heading}")
        lines += [entry_line(n) for n in numbers]
    return lines
