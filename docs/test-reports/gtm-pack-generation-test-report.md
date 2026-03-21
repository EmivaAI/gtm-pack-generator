# GTM Pack Generation — Integration Test Report

## 1. Purpose

This report documents the first integration test of the GTM pack generation pipeline.
The goal was to verify that, given a realistic product launch scenario, the system could produce all six required GTM asset types with coherent, brand-safe, and audience-aware content — using a real LLM call (recorded via VCR cassette for repeatability).

---

## 2. How the Mock Data Was Prepared

### 2.1 Philosophy

Rather than using a trivially simple fixture, the test was designed around a **narrative that mirrors a real-world B2B SaaS launch**. Every piece of mock data was chosen to exercise the context-assembly pipeline end-to-end — including brand constraints, multi-persona audiences, and launch decision metadata.

### 2.2 The Narrative: "Smart Alerts"

The fictional company is **Acme Analytics**, a B2B SaaS platform for data teams monitoring business KPIs in real time.

The product change being launched is **Smart Alerts** — an AI-powered anomaly detection feature that automatically surfaces statistically significant metric drops and spikes.

### 2.3 Mock Data Structure

The following ORM objects were constructed as `MagicMock` instances (no real database required):

#### `ChangeEvent`

| Field | Value |
|---|---|
| `title` | `"Smart Alerts: AI-powered anomaly detection"` |
| `description` | `"Automatically surfaces statistically significant metric drops and spikes to analysts, cutting manual investigation time by ~60%."` |

#### `LaunchCandidate`

| Field | Value |
|---|---|
| `tier` | `TIER_1` |
| `reasons` | High customer impact; addresses #1 support ticket theme |
| `safety_warnings` | None |

#### `BrandProfile`

| Field | Value |
|---|---|
| `product_summary` | B2B SaaS, real-time KPI monitoring for data teams |
| `tone_rules` | Confident but approachable; avoid hype and jargon |
| `allowed_claims` | "60% reduction in investigation time", "SOC 2 Type II certified" |
| `disallowed_claims` | "best in class", "industry leading", "guaranteed ROI" |

#### `AudienceSegment` (two personas)

**Data Analyst**
- Pain points: Too many false-positive alerts, alert fatigue from manual monitoring
- Desired outcomes: Catch real anomalies faster, less time on dashboards
- Objections: "Will it trigger too often?"

**Engineering Manager**
- Pain points: Team spends hours on manual metric review
- Desired outcomes: Reduce on-call burden, confidence in data quality
- Objections: Integration complexity, cost overhead

### 2.4 Database Mock Wiring

Because this is a service-level integration test (not an end-to-end DB test), the SQLAlchemy `Session` was mocked using `unittest.mock.MagicMock`. The mock was wired so that:

- `db.scalar()` returns the `LaunchCandidate`, then the `BrandProfile` (in call order)
- `db.scalars().all()` returns the audience list, then approved assets, then approved candidates
- `db.flush()` assigns a generated UUID to the `GtmPack` to simulate a DB-assigned ID

This approach is codified in the `make_mock_db()` factory function in the test file.

### 2.5 LLM Call Caching (VCR)

Real LLM API calls were made on the first test run and the HTTP responses were recorded to `tests/integration/cassettes/gtm_pack_generation.yaml` using **VCRpy** (`record_mode='once'`). Subsequent runs replay from the cassette, making the test fast and deterministic without mocking the LLM itself. **To refresh the results or test a new model version, the cassette file can be deleted; the next test run will then perform live LLM calls and generate a new record.**

---

## 3. How the GTM Pack Performed

All 6 asset types were generated successfully. The test suite passed every assertion:

| Assert | Result |
|---|---|
| Pack returned and in `DRAFT` status | ✅ |
| `db.flush()` called exactly once | ✅ |
| `db.commit()` called exactly once | ✅ |
| 7 objects added to DB (1 pack + 6 assets) | ✅ |
| All 6 asset types present | ✅ |
| All assets have non-empty `content_draft` | ✅ |
| All assets in `DRAFT` status | ✅ |

### 3.1 Asset-by-Asset Quality Review

#### `INTERNAL_BRIEF`

**Quality: ✅ Strong**

The brief correctly structured itself into Summary, Value Prop, Key Audiences, and FAQs — matching the prompt's format instruction. Both personas (Data Analyst and Engineering Manager) received tailored messaging blocks. The FAQ section addressed objections seeded in the audience fixtures ("Will it trigger too often?", "Integration complexity"). Brand constraints were honoured — the "60% reduction" claim was used; disallowed phrases like "best in class" do not appear.

#### `SALES_SNIPPET`

**Quality: ✅ Strong**

Punchy one-paragraph output, outcome-focused. Leads with the customer pain ("spend less time on dashboards"), transitions to the feature benefit ("60% reduction"), ends with a confidence-building close. Avoids jargon as instructed by tone rules.

#### `SUPPORT_SNIPPET`

**Quality: ✅ Strong**

Well-structured with headers: Introduction, Key Benefits, Addressing Common Concerns, Technical Caveats, and Positioning. Directly addresses both audience objections from the fixture data. SOC 2 Type II claim correctly included as a trust signal. Appropriately longer and more technical in tone than the sales or social assets.

#### `EMAIL` (dual variants)

**Quality: ✅ Good — minor note**

- **Variant A**: Tight and direct. 2 sentences. 
- **Variant B**: Narrative-driven, contextualises the pain, leads through the story, ends on a reassuring confidence note.
- **Note:** The raw `content_draft` stored in the DB includes a wrapping ` ```json ` fence from the prompt output formatting. The downstream consumer (approval UI or renderer) will need to strip this fence before rendering.

#### `LINKEDIN`

**Quality: ✅ Good — minor note**

- **Variant A**: 2-sentence punchy announcement, suitable for a short post.
- **Variant B**: Conversational, question-led opening that hooks the reader before delivering the value. Good social tone.
- **Same note:** ` ```json ` fence present in raw `content_draft`.

#### `CHANGELOG`

**Quality: ✅ Good — minor note**

- **Variant A**: Release-note style, one concise paragraph with the key stat.
- **Variant B**: Longer narrative with "we heard you" positioning. Slightly more marketing-flavoured than a typical changelog entry; may need editorial trimming for pure developer audiences.
- **Same note:** ` ```json ` fence present in raw `content_draft`.


