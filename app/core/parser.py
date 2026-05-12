"""
app/core/parser.py
------------------
Robust Apple Health parser — поддерживает ОБА формата:
  - export.xml     : стандартный Apple Health (HKRecord elements)
  - export_cda.xml : CDA/HL7 формат (observation + <text><type>HK...</type>)

Решает реальные проблемы Apple Health:
  1. Огромные файлы → iterparse / regex streaming (не грузит в память)
  2. Дубликаты из разных источников → приоритет Apple Watch > iPhone > др.
  3. Правильная агрегация → sum для шагов, mean для HR
  4. Sleep intervals → почасовые стадии
  5. Нормализация единиц → lb→kg, mi→km, Cal→kcal

Запуск:
    python app/core/parser.py data/export.xml 30
    python app/core/parser.py data/export_cda.xml 30
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import numpy as np


# ── HK TYPE MAP ───────────────────────────────────────────────────────────────
HK_TYPE_MAP = {
    "HKQuantityTypeIdentifierHeartRate":               "HeartRate",
    "HKQuantityTypeIdentifierRestingHeartRate":        "RestingHeartRate",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":"HRV",
    "HKQuantityTypeIdentifierOxygenSaturation":        "BloodOxygen",
    "HKQuantityTypeIdentifierStepCount":               "Steps",
    "HKQuantityTypeIdentifierActiveEnergyBurned":      "ActiveEnergy",
    "HKQuantityTypeIdentifierBasalEnergyBurned":       "RestingEnergy",
    "HKQuantityTypeIdentifierDistanceWalkingRunning":  "Distance",
    "HKQuantityTypeIdentifierFlightsClimbed":          "FlightsClimbed",
    "HKQuantityTypeIdentifierAppleExerciseTime":       "ExerciseMinutes",
    "HKQuantityTypeIdentifierBodyMass":                "Weight",
    "HKQuantityTypeIdentifierHeight":                  "Height",
    "HKQuantityTypeIdentifierBodyMassIndex":           "BMI",
    "HKQuantityTypeIdentifierBodyFatPercentage":       "BodyFat",
    "HKQuantityTypeIdentifierDietaryEnergyConsumed":   "DietaryCalories",
    "HKQuantityTypeIdentifierDietaryWater":            "Water",
    "HKCategoryTypeIdentifierSleepAnalysis":           "SleepAnalysis",
}

SUM_METRICS = {
    "Steps", "ActiveEnergy", "RestingEnergy", "Distance",
    "FlightsClimbed", "ExerciseMinutes", "DietaryCalories", "Water",
}

SOURCE_PRIORITY = {
    "apple watch": 10, "applewatch": 10,
    "iphone": 6, "health": 5,
    "fitbit": 4, "garmin": 4, "withings": 4,
    "myfitnesspal": 3,
}

UNIT_CONVERSION = {
    "lb":  ("kg",   lambda x: x * 0.453592),
    "lbs": ("kg",   lambda x: x * 0.453592),
    "mi":  ("km",   lambda x: x * 1.60934),
    "Cal": ("kcal", lambda x: x),
    "in":  ("cm",   lambda x: x * 2.54),
}

BOUNDS = {
    "HeartRate":    (30, 220),
    "BloodOxygen":  (70, 100),
    "Steps":        (0, 100_000),
    "Weight":       (20, 300),
    "Height":       (100, 250),
    "ActiveEnergy": (0, 5_000),
    "Distance":     (0, 200),
}

SLEEP_VALUE_MAP = {
    "0": -1, "1": 2,
    "HKCategoryValueSleepAnalysisInBed":      -1,
    "HKCategoryValueSleepAnalysisAsleep":      2,
    "HKCategoryValueSleepAnalysisAwake":       0,
    "HKCategoryValueSleepAnalysisAsleepCore":  1,
    "HKCategoryValueSleepAnalysisAsleepDeep":  3,
    "HKCategoryValueSleepAnalysisAsleepREM":   2,
}

# CDA date format: 20230108134500+0100
CDA_DATE_RE = re.compile(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})')


def _parse_cda_date(s: str):
    """Parse CDA date string like 20230108134500+0100"""
    m = CDA_DATE_RE.match(s.strip())
    if not m:
        return None
    y, mo, d, h, mi = m.groups()
    try:
        # Parse timezone offset if present
        tz_part = s[14:] if len(s) > 14 else "+0000"
        tz_part = tz_part.replace(":", "")
        if tz_part and (tz_part[0] in "+-"):
            sign  = 1 if tz_part[0] == "+" else -1
            hours = int(tz_part[1:3])
            mins  = int(tz_part[3:5]) if len(tz_part) >= 5 else 0
            offset = timezone(timedelta(hours=sign * hours, minutes=sign * mins))
        else:
            offset = timezone.utc
        return datetime(int(y), int(mo), int(d), int(h), int(mi),
                        tzinfo=offset)
    except Exception:
        return None


class HealthParser:
    """
    Универсальный парсер Apple Health.
    Автоматически определяет формат файла.
    """

    def __init__(self, trusted_sources: list = None):
        self.trusted_sources = trusted_sources

    # ── FORMAT DETECTION ──────────────────────────────────────────────────────

    def _detect_format(self, xml_path: str) -> str:
        with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(3000)
        if "ClinicalDocument" in head or "hl7-org" in head:
            return "cda"
        if "HealthData" in head or "<Record " in head:
            return "standard"
        return "cda"  # fallback

    # ── MAIN ENTRY POINT ──────────────────────────────────────────────────────

    def parse(
        self,
        xml_path: str,
        days: int = 30,
        freq: str = "1h",
    ) -> pd.DataFrame:
        """
        Args:
            xml_path : путь к export.xml или export_cda.xml
            days     : последние N дней (None = всё)
            freq     : агрегация ('1h', '1D', '30min')
        Returns:
            pd.DataFrame с временным индексом
        """
        path = Path(xml_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {xml_path}")

        size_mb = path.stat().st_size / 1_048_576
        fmt = self._detect_format(xml_path)
        print(f"📂 Parsing  : {path.name} ({size_mb:.1f} MB)")
        print(f"   Format   : {fmt.upper()}")

        cutoff = None
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            print(f"   Cutoff   : last {days} days")

        if fmt == "cda":
            records = self._parse_cda(xml_path, cutoff)
        else:
            records = self._parse_standard(xml_path, cutoff)

        if not records:
            print("⚠️  No records found in date range.")
            return pd.DataFrame()

        df_raw = pd.DataFrame(records)
        df_raw["start"] = pd.to_datetime(df_raw["start"], utc=True,
                                          errors="coerce")
        df_raw = df_raw.dropna(subset=["start"])
        df_raw["value"] = pd.to_numeric(df_raw["value"], errors="coerce")
        df_raw = df_raw.dropna(subset=["value"])

        print(f"   Records  : {len(df_raw):,}")
        print(f"   Types    : {sorted(df_raw['type'].unique())}")

        # Deduplicate
        df_dedup = self._deduplicate(df_raw)

        # Aggregate to hourly
        df_out = self._aggregate(df_dedup, freq)

        # Sleep
        sleep_rows = df_raw[df_raw["type"] == "SleepAnalysis"]
        if not sleep_rows.empty:
            df_out = self._merge_sleep(df_out, sleep_rows, freq)

        # Clean outliers
        df_out = self._clean_outliers(df_out)

        # Forward fill slowly-changing metrics
        for col in ["Weight", "Height", "BMI", "BodyFat"]:
            if col in df_out.columns:
                df_out[col] = df_out[col].ffill().bfill()

        print(f"✅ Shape     : {df_out.shape}")
        if not df_out.empty:
            print(f"   Range    : {df_out.index.min()} → {df_out.index.max()}")
        if "HeartRate" in df_out.columns:
            hr = df_out["HeartRate"].dropna()
            if len(hr):
                print(f"   HR       : {hr.min():.0f}–{hr.max():.0f} bpm  μ={hr.mean():.1f}")
        if "Steps" in df_out.columns:
            st = df_out["Steps"].dropna()
            if len(st):
                print(f"   Steps/h  : max={st.max():.0f}  μ={st.mean():.1f}")

        return df_out.reset_index()

    # ── STANDARD FORMAT PARSER ────────────────────────────────────────────────

    def _parse_standard(self, xml_path: str, cutoff) -> list:
        """Parse standard export.xml using iterparse."""
        records = []
        context = ET.iterparse(xml_path, events=("start",))
        n = 0
        for event, elem in context:
            if elem.tag == "Record":
                n += 1
                rec = self._parse_hk_record(elem, cutoff)
                if rec:
                    records.append(rec)
                elem.clear()
            elif elem.tag == "Workout":
                elem.clear()
        print(f"   Scanned  : {n:,} Record elements")
        return records

    def _parse_hk_record(self, elem, cutoff) -> dict | None:
        hk_type = elem.get("type", "")
        canon   = HK_TYPE_MAP.get(hk_type)
        if not canon:
            return None

        start_str = elem.get("startDate", "")
        value_str = elem.get("value",     "")
        unit      = elem.get("unit",      "")
        source    = elem.get("sourceName","")

        try:
            s = start_str.strip().replace("Z", "+00:00")
            # Apple export.xml format: "2023-06-26 21:26:08 +0100"
            if " " in s and not s.endswith(")"):
                parts = s.rsplit(" ", 1)
                if len(parts) == 2 and (parts[1].startswith("+") or parts[1].startswith("-")):
                    tz_raw = parts[1]
                    # Convert +0100 → +01:00
                    if ":" not in tz_raw and len(tz_raw) == 5:
                        tz_raw = tz_raw[:3] + ":" + tz_raw[3:]
                    s = parts[0].replace(" ", "T") + tz_raw
            start = datetime.fromisoformat(s)
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
        except Exception:
            return None

        if cutoff and start.astimezone(timezone.utc) < cutoff:
            return None

        # Sleep category
        if canon == "SleepAnalysis":
            end_str = elem.get("endDate", start_str)
            try:
                es = end_str.strip().replace("Z", "+00:00")
                if " " in es:
                    parts = es.rsplit(" ", 1)
                    if len(parts) == 2 and (parts[1].startswith("+") or parts[1].startswith("-")):
                        tz_raw = parts[1]
                        if ":" not in tz_raw and len(tz_raw) == 5:
                            tz_raw = tz_raw[:3] + ":" + tz_raw[3:]
                        es = parts[0].replace(" ", "T") + tz_raw
                end = datetime.fromisoformat(es)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
            except Exception:
                end = start
            return {"type": canon, "start": start, "end": end,
                    "value": value_str, "source": source, "unit": "stage"}

        try:
            value = float(value_str)
        except (ValueError, TypeError):
            return None

        if unit in UNIT_CONVERSION:
            unit, fn = UNIT_CONVERSION[unit][0], UNIT_CONVERSION[unit][1]
            value = fn(value)

        return {"type": canon, "start": start, "value": value,
                "unit": unit, "source": source}

    # ── CDA FORMAT PARSER ─────────────────────────────────────────────────────

    def _parse_cda(self, xml_path: str, cutoff) -> list:
        """
        Parse CDA/HL7 format using regex streaming.
        CDA файл содержит несколько корневых элементов — стандартный
        XML парсер падает. Используем regex по блокам.
        """
        print("   Using CDA regex parser (multi-root XML)...")
        records = []

        # Read in chunks to handle large files
        chunk_size = 10 * 1024 * 1024  # 10 MB chunks
        buffer = ""
        obs_pattern = re.compile(
            r'<observation[^>]*>(.*?)</observation>',
            re.DOTALL
        )

        with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                buffer += chunk

                # Process complete observations
                matches = list(obs_pattern.finditer(buffer))
                if not matches:
                    continue

                # Keep last partial observation in buffer
                last_end = matches[-1].end()
                for m in matches:
                    rec = self._parse_cda_observation(m.group(0), cutoff)
                    if rec:
                        records.append(rec)

                buffer = buffer[last_end:]

            # Process remaining buffer
            for m in obs_pattern.finditer(buffer):
                rec = self._parse_cda_observation(m.group(0), cutoff)
                if rec:
                    records.append(rec)

        return records

    def _parse_cda_observation(self, block: str, cutoff) -> dict | None:
        # Extract HK type
        type_m = re.search(r'<type>(HK[^<]+)</type>', block)
        if not type_m:
            return None
        hk_type = type_m.group(1).strip()
        canon   = HK_TYPE_MAP.get(hk_type)
        if not canon:
            return None

        # Extract value
        val_m = re.search(r'<value>([0-9.]+)</value>', block)
        if not val_m:
            return None
        try:
            value = float(val_m.group(1))
        except ValueError:
            return None

        # Extract date from <low value="..."/>
        date_m = re.search(r'<low value="(\d{12,})', block)
        if not date_m:
            return None
        start = _parse_cda_date(date_m.group(1))
        if not start:
            return None

        if cutoff and start.astimezone(timezone.utc) < cutoff:
            return None

        # Extract unit and source
        unit_m   = re.search(r'<unit>([^<]+)</unit>', block)
        source_m = re.search(r'<sourceName>([^<]+)</sourceName>', block)
        unit     = unit_m.group(1).strip()   if unit_m   else ""
        source   = source_m.group(1).strip() if source_m else ""

        # Unit conversion
        if unit in UNIT_CONVERSION:
            unit, fn = UNIT_CONVERSION[unit][0], UNIT_CONVERSION[unit][1]
            value = fn(value)

        return {"type": canon, "start": start, "value": value,
                "unit": unit, "source": source}

    # ── DEDUPLICATION ─────────────────────────────────────────────────────────

    def _source_priority(self, source: str) -> int:
        s = source.lower()
        for key, prio in SOURCE_PRIORITY.items():
            if key in s:
                return prio
        return 1

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["priority"] = df["source"].apply(self._source_priority)
        df["hour"]     = df["start"].dt.floor("1h")
        df = df.sort_values("priority", ascending=False)
        # Keep best source per (type, hour)
        return df.drop_duplicates(subset=["type", "hour"], keep="first")

    # ── AGGREGATION ───────────────────────────────────────────────────────────

    def _aggregate(self, df: pd.DataFrame, freq: str) -> pd.DataFrame:
        df = df[df["type"] != "SleepAnalysis"].copy()
        df["period"] = df["start"].dt.floor(freq)
        parts = []
        for metric, group in df.groupby("type"):
            fn = "sum" if metric in SUM_METRICS else "mean"
            parts.append(
                group.groupby("period")["value"].agg(fn).rename(metric)
            )
        if not parts:
            return pd.DataFrame()
        result = pd.concat(parts, axis=1)
        result.index.name = "datetime"
        return result

    # ── SLEEP ─────────────────────────────────────────────────────────────────

    def _merge_sleep(self, df, sleep_df, freq):
        sleep_map = {}
        for _, row in sleep_df.iterrows():
            stage = SLEEP_VALUE_MAP.get(str(row["value"]), -1)
            start = pd.Timestamp(row["start"]).floor(freq)
            end   = pd.Timestamp(row.get("end", row["start"])).ceil(freq)
            cur   = start
            while cur <= end:
                if cur not in sleep_map or stage > sleep_map[cur]:
                    sleep_map[cur] = stage
                cur += pd.Timedelta(freq)
        df["SleepStage"] = df.index.map(lambda x: sleep_map.get(x, np.nan))
        df["IsSleeping"] = (df["SleepStage"] >= 0).astype(int)
        return df

    # ── OUTLIER CLEANING ──────────────────────────────────────────────────────

    def _clean_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        fixed = {}
        for col in df.columns:
            if col in BOUNDS:
                lo, hi = BOUNDS[col]
                bad = (df[col] < lo) | (df[col] > hi)
                n = bad.sum()
                if n > 0:
                    df.loc[bad, col] = np.nan
                    fixed[col] = int(n)
        if fixed:
            print(f"   Outliers : {fixed}")
        return df

    # ── CONVENIENCE ───────────────────────────────────────────────────────────

    def to_pipeline_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Переименовывает колонки для UniversalPipeline."""
        rename = {
            "HeartRate":    "HeartRate",
            "ActiveEnergy": "Active Energy",
            "BloodOxygen":  "Blood Oxygen",
            "Steps":        "Steps",
            "Distance":     "Distance",
            "RestingEnergy":"Resting Energy",
            "Weight":       "Weight",
            "Height":       "Height",
            "SleepStage":   "Sleep Analysis",
            "IsSleeping":   "Is Sleeping",
        }
        return df.rename(columns={k: v for k, v in rename.items()
                                   if k in df.columns})


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    xml_path = sys.argv[1] if len(sys.argv) > 1 else "data/export.xml"
    days     = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    parser = HealthParser()
    df = parser.parse(xml_path, days=days)

    if not df.empty:
        out_dir = Path("data")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = str(out_dir / f"parsed_health_{days}days.csv")
        df.to_csv(out, index=False)
        print(f"\n✅ Saved → {out}")
        print(f"\nColumns : {df.columns.tolist()}")
        print(f"\nSample  :\n{df.head(3).to_string()}")
    else:
        print("⚠️  Empty result — check date range")