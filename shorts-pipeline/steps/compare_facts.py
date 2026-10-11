"""Số liệu thật Nhật Bản so với một nước khác, cho kiểu chuyện "Nhật Bản vs nước khác" (tân bốc Nhật bằng số liệu).

  python steps/compare_facts.py CHN          # in thử

Nguồn: World Bank Open Data (api.worldbank.org, miễn phí, không cần khóa), giá trị mới nhất có số của từng nước.
steps/01_script.py lấy các chỉ số Nhật hơn nước kia, đưa vào lời dặn để AI chỉ dùng đúng số này (không tự bịa số).
"""
import json
import sys

import requests

# ISO3 -> (tên tiếng Việt, tên tiếng Nhật). Đài Loan, Hồng Kông không có trong World Bank nên không có ở đây.
COUNTRIES = {
    "CHN": ("Trung Quốc", "中国"), "KOR": ("Hàn Quốc", "韓国"), "USA": ("Mỹ", "アメリカ"), "VNM": ("Việt Nam", "ベトナム"),
    "IND": ("Ấn Độ", "インド"), "THA": ("Thái Lan", "タイ"), "PHL": ("Philippines", "フィリピン"),
    "IDN": ("Indonesia", "インドネシア"), "GBR": ("Anh", "イギリス"), "FRA": ("Pháp", "フランス"), "DEU": ("Đức", "ドイツ"),
    "RUS": ("Nga", "ロシア"), "BRA": ("Brazil", "ブラジル"),
}
# mã chỉ số -> (tên tiếng Nhật, đơn vị, số nhỏ hơn là tốt hơn)
INDICATORS = {
    "SP.DYN.LE00.IN": ("平均寿命", "歳", False),
    "VC.IHR.PSRC.P5": ("殺人発生率（10万人あたり）", "件", True),
    "SH.STA.TRAF.P5": ("交通事故の死亡率（10万人あたり）", "人", True),
    "SP.DYN.IMRT.IN": ("乳児死亡率（1000人あたり）", "人", True),
    "EN.ATM.PM25.MC.M3": ("PM2.5の濃度", "µg/m³", True),
    "SH.STA.SMSS.ZS": ("安全なトイレ・下水を使える人の割合", "%", False),
    "SH.H2O.SMDW.ZS": ("安全な水道水を飲める人の割合", "%", False),
    "SL.UEM.TOTL.ZS": ("失業率", "%", True),
    "NY.GDP.PCAP.CD": ("1人あたりGDP", "ドル", False),
    "IT.NET.USER.ZS": ("インターネット利用率", "%", False),
}
API = "https://api.worldbank.org/v2/country/JPN;{iso}/indicator/{code}"


def fetch(iso):
    """Mọi chỉ số có số của cả hai nước: [{"name", "unit", "japan", "other", "year_japan", "year_other", "japan_better"}]."""
    rows = []
    for code, (name, unit, lower_better) in INDICATORS.items():
        try:
            data = requests.get(API.format(iso=iso, code=code), params={"format": "json", "mrnev": 1}, timeout=20).json()
        except (requests.RequestException, ValueError):
            continue
        values = {x["countryiso3code"]: (x["value"], x["date"]) for x in (data[1] if len(data) > 1 and data[1] else [])
                  if x["value"] is not None}
        if "JPN" not in values or iso not in values:
            continue
        (jp, jp_year), (ot, ot_year) = values["JPN"], values[iso]
        rows.append({"name": name, "unit": unit, "japan": round(jp, 2), "other": round(ot, 2), "year_japan": jp_year,
                     "year_other": ot_year, "japan_better": jp < ot if lower_better else jp > ot})
    return rows


if __name__ == "__main__":
    for row in fetch(sys.argv[1] if len(sys.argv) > 1 else "CHN"):
        print(json.dumps(row, ensure_ascii=False))
