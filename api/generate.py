from http.server import BaseHTTPRequestHandler
import json
import re
import traceback
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

# --- Constants & configuration -------------------------------------------------

MAX_LOG_ENTRIES = 100
MAX_INPUT_LENGTH = 100_000

FIELD_VARIATIONS: Dict[str, List[str]] = {
    "product_name": [
        "商品名", "品名", "製品名", "名前", "商品", "品目",
        "product name", "product", "name", "商品の名前"
    ],
    "product_type": [
        "名称", "品種", "種類", "type", "分類", "品目名",
        "商品の種類", "商品種別", "category"
    ],
    "ingredients": [
        "原材料", "原材料名", "原料", "成分", "ingredients",
        "使用原材料", "材料", "配合成分", "原材料等"
    ],
    "content": [
        "内容量", "容量", "量", "volume", "content", "内容",
        "正味量", "net weight", "入数", "個数"
    ],
    "expiry": [
        "賞味期限", "消費期限", "期限", "expiry", "best before",
        "賞味", "消費", "有効期限", "保存期間"
    ],
    "storage": [
        "保存方法", "保管方法", "保存", "storage",
        "貯蔵方法", "取扱方法", "保存の方法", "保管の方法"
    ],
    "seller": [
        "販売者", "売主", "販売", "seller", "販売元", "販売業者",
        "販売会社", "distributor", "発売元", "販売店"
    ],
    "manufacturer": [
        "製造者", "製造元", "製造", "manufacturer", "製造業者",
        "製造会社", "maker", "メーカー", "製造場所"
    ],
    "processor": [
        "加工者", "加工元", "加工", "processor", "加工業者",
        "加工会社", "加工場所"
    ],
    "importer": [
        "輸入者", "輸入元", "輸入", "importer", "輸入業者",
        "輸入会社", "輸入元会社"
    ],
}

NUTRITION_VARIATIONS: Dict[str, List[str]] = {
    "energy": [
        "エネルギー", "energy", "カロリー", "calorie", "kcal",
        "熱量", "calories", "エネルギー量"
    ],
    "protein": [
        "たんぱく質", "タンパク質", "蛋白質", "protein",
        "たんぱく", "タンパク", "プロテイン"
    ],
    "fat": [
        "脂質", "脂肪", "fat", "lipid", "油脂", "脂肪分"
    ],
    "carbs": [
        "炭水化物", "糖質", "carbohydrate", "carbs", "炭水化物量"
    ],
    "salt": [
        "食塩相当量", "食塩", "塩分", "salt"
    ],
    "sodium": [
        "ナトリウム", "ナトリウム量", "sodium", "Na"
    ],
    "sugar": [
        "糖質", "糖類", "sugar", "sugars", "炭水化物(糖質)"
    ],
    "fiber": [
        "食物繊維", "繊維", "fiber", "dietary fiber", "繊維質"
    ],
}

FIELD_VARIATION_SET = {v.lower() for variations in FIELD_VARIATIONS.values() for v in variations}
NUTRITION_VARIATION_SET = {v.lower() for variations in NUTRITION_VARIATIONS.values() for v in variations}
ALL_KNOWN_FIELD_NAMES = FIELD_VARIATION_SET | NUTRITION_VARIATION_SET

NUTRITION_PRIORITY = ["energy", "protein", "fat", "carbs", "salt"]

DANGEROUS_PATTERNS = [
    "<script", "<iframe", "javascript:", "<object", "<embed", "onerror="
]

BULLET_PATTERN = re.compile(r"^[\\s・\-\*・]+", re.MULTILINE)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
MULTISPACE_PATTERN = re.compile(r"  +")
MULTINEWLINE_PATTERN = re.compile(r"\n{3,}")
FIELD_BLOCK_PATTERN = re.compile(r"[■【\[]?\s*(.+?)\s*[:：]\s*(.+?)(?=\n[■【\[]|【|※|$)", re.DOTALL)

# --- Dataclasses ----------------------------------------------------------------

@dataclass
class ParseLog:
    level: str
    message: str
    field: Optional[str] = None


@dataclass
class ProductInfo:
    product_name: Optional[str] = None
    product_type: Optional[str] = None
    ingredients: Optional[str] = None
    content: Optional[str] = None
    expiry: Optional[str] = None
    storage: Optional[str] = None
    seller: Optional[str] = None
    manufacturer: Optional[str] = None
    processor: Optional[str] = None
    importer: Optional[str] = None

    nutrition: Dict[str, str] = field(default_factory=dict)
    allergen: Optional[str] = None
    extra_fields: Dict[str, str] = field(default_factory=dict)


# --- Utility functions ----------------------------------------------------------


def escape_html(text: str) -> str:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
    return escaped.replace("\n", "<br>")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("　", " ")
    text = text.replace("\t", " ")
    text = text.replace("：", ":")
    text = MULTISPACE_PATTERN.sub(" ", text)
    text = MULTINEWLINE_PATTERN.sub("\n\n", text)
    return text.strip()


def preprocess_extreme_cases(text: str) -> str:
    without_html = HTML_TAG_PATTERN.sub("", text)
    without_bullets = BULLET_PATTERN.sub("", without_html)
    normalized_units = (
        without_bullets
        .replace("グラム", "g")
        .replace("ｇ", "g")
        .replace("キロカロリー", "kcal")
    )
    return normalized_units


def merge_broken_lines(text: str) -> str:
    lines = text.split("\n")
    merged: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            merged.append(line)
            i += 1
            continue

        if (":" not in line and i + 1 < len(lines)):
            value_lines: List[str] = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    break
                if next_line.startswith("■") or next_line.startswith("【"):
                    break
                if re.match(r"^[^:：]+[:：]", next_line):
                    break
                value_lines.append(next_line)
                j += 1

            if value_lines:
                merged.append(f"{line}:{' '.join(value_lines)}")
                i = j
                continue

        merged.append(line)
        i += 1

    return "\n".join(merged)


def validate_input_safety(text: str) -> None:
    if len(text) > MAX_INPUT_LENGTH:
        raise ValueError("入力が長すぎます（最大100KB）")

    lowered = text.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in lowered:
            raise ValueError(f"禁止されたパターン『{pattern}』が含まれています")


def extract_field_value(text: str, field_key: str) -> Optional[str]:
    variations = FIELD_VARIATIONS.get(field_key, [])
    for variation in variations:
        pattern1 = rf"[■【\[]?\s*{re.escape(variation)}\s*[:：]\s*(.+?)(?=\n[■【\[]|【栄養|※|$)"
        match = re.search(pattern1, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        pattern2 = rf"^\s*{re.escape(variation)}\s*[:：]\s*(.+?)(?=\n|$)"
        match = re.search(pattern2, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()

        pattern3 = rf"{re.escape(variation)}\s*\n\s*(.+?)(?=\n|$)"
        match = re.search(pattern3, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_nutrition_flexible(text: str) -> Dict[str, str]:
    results: Dict[str, str] = {}
    numeric_pattern = r"([0-9]+(?:\.[0-9]+)?)"
    unit_pattern = r"([a-zA-Zμ％%/\.ーァ-ヶー]+)?"
    for key, variations in NUTRITION_VARIATIONS.items():
        for variation in variations:
            patterns = [
                rf"{re.escape(variation)}\s*[:：\s]+{numeric_pattern}\s*{unit_pattern}",
                rf"{re.escape(variation)}\s*[（(]\s*{numeric_pattern}\s*{unit_pattern}\s*[）)]",
                rf"{re.escape(variation)}\s*[:：\s]+{numeric_pattern}\s*$",
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    number = match.group(1).strip()
                    unit = match.group(2) or ""
                    unit_normalized = unit.strip()
                    unit_lower = unit_normalized.lower()
                    if "キロカロリー" in unit_normalized or "ｋｃａｌ" in unit_normalized or "kcal" in unit_lower:
                        unit_normalized = "kcal"
                    elif unit_lower in {"ｇ", "g"}:
                        unit_normalized = "g"
                    elif unit_lower in {"ｍｇ", "mg"}:
                        unit_normalized = "mg"
                    results[key] = f"{number}{unit_normalized}" if unit_normalized else number
                    break
            if key in results:
                break
    return results


def convert_sodium_to_salt(nutrition: Dict[str, str]) -> Dict[str, str]:
    if "salt" not in nutrition and "sodium" in nutrition:
        sodium_str = nutrition["sodium"]
        match = re.search(r"(\d+\.?\d*)", sodium_str)
        if match:
            sodium_value = float(match.group(1))
            if "mg" in sodium_str.lower():
                salt_value = sodium_value * 2.54 / 1000
            elif "g" in sodium_str.lower():
                salt_value = sodium_value * 2.54
            else:
                salt_value = sodium_value * 2.54 / 1000
            nutrition["salt"] = f"{salt_value:.1f}g"
    return nutrition


def extract_unknown_fields(text: str) -> Dict[str, str]:
    unknown: Dict[str, str] = {}
    for match in FIELD_BLOCK_PATTERN.finditer(text):
        field_name = match.group(1).strip()
        value = match.group(2).strip()
        if not field_name:
            continue
        field_lower = field_name.lower()
        if field_lower in ALL_KNOWN_FIELD_NAMES:
            continue
        if len(field_name) >= 20:
            continue
        unknown[field_name] = value
    return unknown


def extract_allergen(text: str) -> Optional[str]:
    patterns = [
        r"※(.+?)$",
        r"注意[:：\s]+(.+?)$",
        r"アレルギー[:：\s]+(.+?)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def parse_csv_flexible(csv_content: str) -> str:
    lines = [line for line in csv_content.splitlines() if line.strip()]
    if not lines:
        return csv_content

    delimiters = [",", "\t", ";", "|"]
    best_delim = ","
    max_cols = 0
    for delim in delimiters:
        cols = lines[0].split(delim)
        if len(cols) > max_cols:
            max_cols = len(cols)
            best_delim = delim

    if max_cols < 2:
        return csv_content

    start_index = 0
    header_hint = re.search(r"項目|field|key|name", lines[0], re.IGNORECASE)
    if header_hint:
        start_index = 1

    text_lines: List[str] = []
    for line in lines[start_index:]:
        if not line.strip() or line.strip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split(best_delim)]
        if len(parts) < 2:
            continue
        key, value = parts[0], parts[1]
        if not key or not value:
            continue

        key_lower = key.lower()
        is_nutrition = key_lower in NUTRITION_VARIATION_SET
        if is_nutrition:
            text_lines.append(f"{key}:{value}")
        else:
            text_lines.append(f"■{key}:{value}")

    if not text_lines:
        return csv_content

    has_nutrition = any(not line.startswith("■") for line in text_lines)
    if not has_nutrition:
        return "\n".join(text_lines)

    output: List[str] = []
    nutrition_started = False
    for line in text_lines:
        if not line.startswith("■") and not nutrition_started:
            output.append("【栄養成分表示(100g当たり)】（推定値）")
            nutrition_started = True
        output.append(line)
    return "\n".join(output)


# --- Parser & generator ---------------------------------------------------------


class FlexibleParser:
    def __init__(self) -> None:
        self.logs: List[ParseLog] = []

    def _log(self, level: str, message: str, field: Optional[str] = None) -> None:
        self.logs.append(ParseLog(level=level, message=message, field=field))

    def parse(self, text: str) -> ProductInfo:
        self.logs = []

        if not text or not text.strip():
            self._log("warning", "入力テキストが空です")
            return ProductInfo()

        processed = preprocess_extreme_cases(text)
        processed = normalize_text(processed)
        processed = merge_broken_lines(processed)

        product_data: Dict[str, Any] = {}
        for field_key in FIELD_VARIATIONS.keys():
            value = extract_field_value(processed, field_key)
            if value:
                product_data[field_key] = value
                self._log("info", f"{field_key}を抽出: {value[:30]}...", field_key)
            else:
                self._log("warning", f"{field_key}が見つかりませんでした", field_key)

        nutrition = extract_nutrition_flexible(processed)
        nutrition = convert_sodium_to_salt(nutrition)
        if nutrition:
            for key, value in nutrition.items():
                self._log("info", f"栄養成分 {key}: {value}", f"nutrition.{key}")
        else:
            self._log("warning", "栄養成分が見つかりませんでした", "nutrition")

        allergen = extract_allergen(processed)
        if allergen:
            self._log("info", f"注意書きを抽出: {allergen[:50]}...", "allergen")

        extra_fields = extract_unknown_fields(processed)
        if extra_fields:
            for name, value in extra_fields.items():
                self._log("info", f"未知の項目『{name}』: {value[:30]}...", f"extra.{name}")

        return ProductInfo(
            **product_data,
            nutrition=nutrition,
            allergen=allergen,
            extra_fields=extra_fields,
        )


class HTMLGenerator:
    COLORS = {
        "header_bg": "#f5f5f5",
        "label_bg": "#e8e8e8",
        "border": "#333",
        "allergen_border": "#ff6b6b",
        "allergen_bg": "#fff5f5",
    }

    FIELD_LABELS_JP = {
        "product_name": "商品名",
        "product_type": "名称",
        "ingredients": "原材料",
        "content": "内容量",
        "expiry": "賞味期限",
        "storage": "保存方法",
        "seller": "販売者",
        "manufacturer": "製造者",
        "processor": "加工者",
        "importer": "輸入者",
    }

    NUTRITION_LABELS_JP = {
        "energy": "エネルギー",
        "protein": "たんぱく質",
        "fat": "脂質",
        "carbs": "炭水化物",
        "salt": "食塩相当量",
        "sugar": "糖質",
        "fiber": "食物繊維",
        "sodium": "ナトリウム",
    }

    def generate_all(self, data: ProductInfo) -> Dict[str, str]:
        return {
            "rakuten_pc": self.generate_rakuten_pc(data),
            "rakuten_sp": self.generate_rakuten_sp(data),
            "yahoo_pc": self.generate_yahoo_pc(data),
            "yahoo_sp": self.generate_yahoo_sp(data),
        }

    def _create_table_row_pc(self, label: str, value: str) -> str:
        label_escaped = escape_html(label)
        value_escaped = escape_html(value)
        return (
            "<tr>\n"
            "      <th style=\"background:{label_bg};padding:10px;border:1px solid {border};text-align:left;width:25%;\">{label}</th>\n"
            "      <td style=\"padding:10px;border:1px solid {border};\">{value}</td>\n"
            "    </tr>"
        ).format(label_bg=self.COLORS["label_bg"], border=self.COLORS["border"], label=label_escaped, value=value_escaped)

    def _create_nutrition_row_pc(self, label: str, value: str) -> str:
        return self._create_table_row_pc(label, value)

    def _wrap_in_table_pc(self, title: str, rows_html: str) -> str:
        title_escaped = escape_html(title)
        return (
            f"<div style=\"margin-bottom:20px;\">\n"
            f"  <div style=\"background:{self.COLORS['header_bg']};padding:12px 16px;border:1px solid {self.COLORS['border']};font-weight:bold;\">{title_escaped}</div>\n"
            f"  <table style=\"width:100%;border-collapse:collapse;font-size:14px;\">\n    {rows_html}\n  </table>\n"
            "</div>"
        )

    def _build_product_rows_pc(self, data: ProductInfo) -> List[str]:
        rows: List[str] = []
        for field_key in [
            "product_name",
            "product_type",
            "ingredients",
            "content",
            "expiry",
            "storage",
            "seller",
            "manufacturer",
            "processor",
            "importer",
        ]:
            value = getattr(data, field_key)
            if value:
                label = self.FIELD_LABELS_JP.get(field_key, field_key)
                rows.append(self._create_table_row_pc(label, value))
        for field_name, value in data.extra_fields.items():
            rows.append(self._create_table_row_pc(field_name, value))
        return rows

    def _build_nutrition_rows_pc(self, nutrition: Dict[str, str]) -> List[str]:
        rows: List[str] = []
        for key in NUTRITION_PRIORITY:
            if key in nutrition:
                label = self.NUTRITION_LABELS_JP.get(key, key)
                rows.append(self._create_nutrition_row_pc(label, nutrition[key]))
        for key, value in nutrition.items():
            if key in NUTRITION_PRIORITY:
                continue
            label = self.NUTRITION_LABELS_JP.get(key, key)
            rows.append(self._create_nutrition_row_pc(label, value))
        return rows

    def _build_allergen_section_pc(self, allergen: str) -> str:
        return (
            f"<div style=\"border:2px solid {self.COLORS['allergen_border']};background:{self.COLORS['allergen_bg']};padding:16px;margin-top:20px;\">\n"
            f"  <strong>注意事項</strong><br>{escape_html(allergen)}\n"
            "</div>"
        )

    def generate_rakuten_pc(self, data: ProductInfo) -> str:
        product_rows = self._build_product_rows_pc(data)
        nutrition_rows = self._build_nutrition_rows_pc(data.nutrition)
        sections = []
        if product_rows:
            sections.append(self._wrap_in_table_pc("商品情報", "\n    ".join(product_rows)))
        if nutrition_rows:
            sections.append(self._wrap_in_table_pc("栄養成分表示（100g当たり）推定値", "\n    ".join(nutrition_rows)))
        if data.allergen:
            sections.append(self._build_allergen_section_pc(data.allergen))
        if not sections:
            return "<div style=\"padding:20px;color:#999;\">情報を抽出できませんでした</div>"
        return (
            "<div style=\"margin:20px auto;max-width:800px;font-family:'メイリオ',Meiryo,sans-serif;\">\n  "
            + "\n  ".join(sections)
            + "\n</div>"
        )

    def _build_product_rows_sp(self, data: ProductInfo) -> List[str]:
        rows: List[str] = []
        for field_key in [
            "product_name",
            "product_type",
            "ingredients",
            "content",
            "expiry",
            "storage",
            "seller",
            "manufacturer",
            "processor",
            "importer",
        ]:
            value = getattr(data, field_key)
            if value:
                label = self.FIELD_LABELS_JP.get(field_key, field_key)
                rows.append(self._wrap_sp_item(label, value))
        for field_name, value in data.extra_fields.items():
            rows.append(self._wrap_sp_item(field_name, value))
        return rows

    def _build_nutrition_rows_sp(self, nutrition: Dict[str, str]) -> List[str]:
        rows: List[str] = []
        for key in NUTRITION_PRIORITY:
            if key in nutrition:
                label = self.NUTRITION_LABELS_JP.get(key, key)
                rows.append(self._wrap_sp_item(label, nutrition[key]))
        for key, value in nutrition.items():
            if key in NUTRITION_PRIORITY:
                continue
            label = self.NUTRITION_LABELS_JP.get(key, key)
            rows.append(self._wrap_sp_item(label, value))
        return rows

    def _wrap_sp_item(self, label: str, value: str) -> str:
        return (
            f"<table width=\"100%\" cellpadding=\"10\" cellspacing=\"0\" style=\"border:1px solid {self.COLORS['border']};background:#fff;margin-bottom:8px;\">"
            f"<tr><td style=\"font-weight:bold;color:#555;border-bottom:1px solid #ddd;\">{escape_html(label)}</td></tr>"
            f"<tr><td style=\"line-height:1.6;\">{escape_html(value)}</td></tr>"
            "</table>"
        )

    def _wrap_in_table_sp(self, title: str, body: str) -> str:
        return (
            f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin-bottom:16px;\">"
            f"<tr><td style=\"background:{self.COLORS['header_bg']};padding:10px 12px;font-weight:bold;\">{escape_html(title)}</td></tr>"
            f"<tr><td style=\"padding:12px;background:#fafafa;\">{body}</td></tr>"
            "</table>"
        )

    def _build_allergen_section_sp(self, allergen: str) -> str:
        return (
            f"<table width=\"100%\" cellpadding=\"12\" cellspacing=\"0\" style=\"border:2px solid {self.COLORS['allergen_border']};background:{self.COLORS['allergen_bg']};margin-top:16px;\">"
            f"<tr><td><b>注意事項</b><br>{escape_html(allergen)}</td></tr>"
            "</table>"
        )

    def generate_rakuten_sp(self, data: ProductInfo) -> str:
        product_rows = self._build_product_rows_sp(data)
        nutrition_rows = self._build_nutrition_rows_sp(data.nutrition)
        sections: List[str] = []
        if product_rows:
            sections.append(self._wrap_in_table_sp("商品情報", "".join(product_rows)))
        if nutrition_rows:
            sections.append(self._wrap_in_table_sp("栄養成分表示（100g当たり）推定値", "".join(nutrition_rows)))
        if data.allergen:
            sections.append(self._build_allergen_section_sp(data.allergen))
        if not sections:
            return "<p>情報を抽出できませんでした</p>"
        return "<br>".join(sections)

    def _wrap_dl(self, label: str, value: str) -> str:
        return (
            f"<dt style=\"font-weight:bold;color:#444;margin-bottom:4px;\">{escape_html(label)}</dt>"
            f"<dd style=\"margin:0 0 12px 0;padding-bottom:12px;border-bottom:1px solid {self.COLORS['border']};\">{escape_html(value)}</dd>"
        )

    def generate_yahoo_pc(self, data: ProductInfo) -> str:
        items: List[str] = []
        for field_key in [
            "product_name",
            "product_type",
            "ingredients",
            "content",
            "expiry",
            "storage",
            "seller",
            "manufacturer",
            "processor",
            "importer",
        ]:
            value = getattr(data, field_key)
            if value:
                label = self.FIELD_LABELS_JP.get(field_key, field_key)
                items.append(self._wrap_dl(label, value))
        for field_name, value in data.extra_fields.items():
            items.append(self._wrap_dl(field_name, value))
        nutrition_items: List[str] = []
        for key in NUTRITION_PRIORITY:
            if key in data.nutrition:
                label = self.NUTRITION_LABELS_JP.get(key, key)
                nutrition_items.append(self._wrap_dl(label, data.nutrition[key]))
        for key, value in data.nutrition.items():
            if key in NUTRITION_PRIORITY:
                continue
            label = self.NUTRITION_LABELS_JP.get(key, key)
            nutrition_items.append(self._wrap_dl(label, value))

        parts: List[str] = []
        if items:
            parts.append(
                "<section style=\"margin-bottom:24px;font-family:'ヒラギノ角ゴ ProN',sans-serif;\">\n"
                "  <h2 style=\"font-size:18px;border-bottom:2px solid #333;padding-bottom:6px;\">商品情報</h2>\n"
                "  <dl style=\"margin:16px 0;\">" + "".join(items) + "</dl>\n"
                "</section>"
            )
        if nutrition_items:
            parts.append(
                "<section style=\"margin-bottom:24px;font-family:'ヒラギノ角ゴ ProN',sans-serif;\">\n"
                "  <h2 style=\"font-size:18px;border-bottom:2px solid #333;padding-bottom:6px;\">栄養成分表示（100g当たり）推定値</h2>\n"
                "  <dl style=\"margin:16px 0;\">" + "".join(nutrition_items) + "</dl>\n"
                "</section>"
            )
        if data.allergen:
            parts.append(
                f"<section style=\"border:2px solid {self.COLORS['allergen_border']};padding:16px;background:{self.COLORS['allergen_bg']};\">\n"
                "  <h2 style=\"margin-top:0;\">注意事項</h2>\n"
                f"  <p style=\"margin:0;\">{escape_html(data.allergen)}</p>\n"
                "</section>"
            )
        if not parts:
            return "<div style=\"padding:16px;color:#666;\">情報を抽出できませんでした</div>"
        return "".join(parts)

    def generate_yahoo_sp(self, data: ProductInfo) -> str:
        blocks: List[str] = []
        for field_key in [
            "product_name",
            "product_type",
            "ingredients",
            "content",
            "expiry",
            "storage",
            "seller",
            "manufacturer",
            "processor",
            "importer",
        ]:
            value = getattr(data, field_key)
            if value:
                label = self.FIELD_LABELS_JP.get(field_key, field_key)
                blocks.append(self._wrap_sp_item(label, value))
        for field_name, value in data.extra_fields.items():
            blocks.append(self._wrap_sp_item(field_name, value))
        if data.nutrition:
            nutri_blocks = []
            for key in NUTRITION_PRIORITY:
                if key in data.nutrition:
                    label = self.NUTRITION_LABELS_JP.get(key, key)
                    nutri_blocks.append(self._wrap_sp_item(label, data.nutrition[key]))
            for key, value in data.nutrition.items():
                if key in NUTRITION_PRIORITY:
                    continue
                label = self.NUTRITION_LABELS_JP.get(key, key)
                nutri_blocks.append(self._wrap_sp_item(label, value))
            blocks.append(
                f"<table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"margin-top:16px;\">"
                f"<tr><td style=\"font-weight:bold;padding-bottom:8px;\">栄養成分表示（100g当たり）推定値</td></tr>"
                f"<tr><td>{''.join(nutri_blocks)}</td></tr>"
                f"</table>"
            )
        if data.allergen:
            blocks.append(self._build_allergen_section_sp(data.allergen))
        if not blocks:
            return "<p>情報を抽出できませんでした</p>"
        return "<br>".join(blocks)


# --- Core orchestrator ----------------------------------------------------------


def product_info_to_serializable(info: ProductInfo) -> Dict[str, Any]:
    data = asdict(info)
    return data


def logs_to_serializable(logs: List[ParseLog]) -> List[Dict[str, Any]]:
    return [asdict(log) for log in logs][:MAX_LOG_ENTRIES]


def process_input(text: str, input_type: str = "text") -> Dict[str, Any]:
    debug_logs: List[str] = []
    user_logs: List[str] = []

    try:
        if text is None:
            raise ValueError("テキストが指定されていません")
        if not isinstance(text, str):
            text = str(text)

        validate_input_safety(text)
        debug_logs.append(f"input_length={len(text)}")

        working_text = text
        if input_type == "csv":
            debug_logs.append("CSV入力を検出。テキストへ変換します。")
            working_text = parse_csv_flexible(text)
            user_logs.append("CSVを解析してテキストに変換しました。")

        parser = FlexibleParser()
        product_info = parser.parse(working_text)

        generator = HTMLGenerator()
        html_map = generator.generate_all(product_info)

        user_logs.append("解析とHTML生成が完了しました。")
        debug_logs.append("html_variants=" + ",".join(html_map.keys()))

        response = {
            "success": True,
            "html": html_map,
            "product_info": product_info_to_serializable(product_info),
            "logs": logs_to_serializable(parser.logs),
            "user_logs": user_logs[:MAX_LOG_ENTRIES],
            "debug_logs": debug_logs[:MAX_LOG_ENTRIES],
            "normalized_text": working_text,
            "input_type": input_type,
            "status_code": 200,
        }
        return response
    except ValueError as exc:
        message = str(exc)
        user_logs.append(message)
        debug_logs.append(f"validation_error:{message}")
        return {
            "success": False,
            "error": message,
            "user_logs": user_logs[:MAX_LOG_ENTRIES],
            "debug_logs": debug_logs[:MAX_LOG_ENTRIES],
            "status_code": 400,
        }
    except Exception:
        debug_logs.append("unexpected_server_error")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": "サーバー内部でエラーが発生しました。時間を置いて再度お試しください。",
            "user_logs": user_logs[:MAX_LOG_ENTRIES],
            "debug_logs": debug_logs[:MAX_LOG_ENTRIES],
            "status_code": 500,
        }



# --- HTTP handler ----------------------------------------------------------------


class handler(BaseHTTPRequestHandler):
    def _set_headers(self) -> None:
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:  # noqa: N802 (Vercel expects this name)
        self.send_response(200)
        self._set_headers()
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        try:
            length_header = self.headers.get("Content-Length")
            content_length = int(length_header) if length_header else 0
            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            error_response = {
                "success": False,
                "error": "JSONの解析に失敗しました",
            }
            self.send_response(400)
            self._set_headers()
            self.end_headers()
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode("utf-8"))
            return
        except Exception:  # pragma: no cover - defensive
            error_response = {
                "success": False,
                "error": "リクエストの読み込みに失敗しました。",
            }
            self.send_response(500)
            self._set_headers()
            self.end_headers()
            print(traceback.format_exc())
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode("utf-8"))
            return

        text = payload.get("text", "")
        input_type = payload.get("type", "text")
        result = process_input(text, input_type)

        status_code = result.pop("status_code", 200)
        self.send_response(status_code)
        self._set_headers()
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))



