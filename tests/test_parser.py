import unittest

from api.generate import FlexibleParser, process_input


TEST_CASES = [
    {
        "name": "標準入力_完全",
        "input": """■商品名：蒜山高原ミックスチョコレート\n■名称：チョコレート\n■原材料：チョコレート(砂糖、ココアバター...)\n■内容量：300g\n■賞味期限：製造より180日\n■保存方法：28℃以下で保存\n■販売者：株式会社天然生活\n【栄養成分表示(100g当たり)】（推定値）\nエネルギー：595kcal\nたんぱく質：6.7g\n脂質：41.0g\n炭水化物：49.9g\n食塩相当量：0.3g\n※本品製造工場では...""",
        "expected": {
            "has_product_name": True,
            "has_nutrition": True,
            "content_value": "300g",
        },
    },
    {
        "name": "順番バラバラ",
        "input": """■販売者：株式会社天然生活\n■原材料：チョコレート\n■商品名：チョコレート\nエネルギー：595kcal\n■名称：菓子\nたんぱく質：6.7g""",
        "expected": {
            "has_product_name": True,
        },
    },
    {
        "name": "項目名_表記ゆれ",
        "input": """品名：チョコレート\n製品名：ミックスチョコ\n原料：砂糖\nカロリー：595kcal\nタンパク質：6.7g""",
        "expected": {
            "has_product_name": True,
        },
    },
    {
        "name": "全角半角混在",
        "input": """■商品名：チョコレート\n■名称：菓子\nエネルギー：５９５kcal\nたんぱく質：６．７ｇ""",
        "expected": {
            "has_nutrition": True,
        },
    },
    {
        "name": "コロン_バリエーション",
        "input": """商品名:チョコレート\n名称：菓子\n原材料 砂糖\nエネルギー  595kcal""",
        "expected": {},
    },
    {
        "name": "改行まみれ",
        "input": """商品名\nチョコレート\nミックス\n\n名称\n菓子\n\nエネルギー\n595\nkcal""",
        "expected": {
            "has_product_name": True,
            "has_nutrition": True,
        },
    },
    {
        "name": "ナトリウム換算",
        "input": """商品名：チョコ\n名称：菓子\n原材料：砂糖\nエネルギー：595kcal\nたんぱく質：6.7g\n脂質：41.0g\n炭水化物：49.9g\nナトリウム：118mg""",
        "expected": {
            "has_salt_converted": True,
        },
    },
    {
        "name": "最小限",
        "input": """商品名：チョコ\n名称：菓子\n原材料：砂糖\nエネルギー：595kcal\nたんぱく質：6.7g\n脂質：41.0g\n炭水化物：49.9g\n食塩相当量：0.3g""",
        "expected": {
            "has_product_name": True,
            "has_nutrition": True,
        },
    },
    {
        "name": "栄養成分のみ",
        "input": """エネルギー：595kcal\nたんぱく質：6.7g\n脂質：41.0g\n炭水化物：49.9g\n食塩相当量：0.3g""",
        "expected": {
            "warning_count": lambda count: count > 0,
        },
    },
    {
        "name": "商品情報のみ",
        "input": """商品名：チョコレート\n名称：菓子\n原材料：砂糖、カカオ\n販売者：株式会社天然生活""",
        "expected": {
            "warning_count": lambda count: count > 0,
        },
    },
]


class FlexibleParserSpecTests(unittest.TestCase):
    def test_parser_cases(self) -> None:
        for case in TEST_CASES:
            with self.subTest(case=case["name"]):
                parser = FlexibleParser()
                product_info = parser.parse(case["input"])
                logs = parser.logs
                expected = case["expected"]

                if expected.get("has_product_name"):
                    self.assertIsNotNone(
                        product_info.product_name,
                        msg=f"product_name missing for {case['name']}",
                    )

                if expected.get("has_nutrition"):
                    self.assertGreater(
                        len(product_info.nutrition),
                        0,
                        msg=f"nutrition missing for {case['name']}",
                    )

                if expected.get("content_value") is not None:
                    self.assertEqual(
                        expected["content_value"],
                        product_info.content,
                        msg=f"content mismatch for {case['name']}",
                    )

                if expected.get("has_salt_converted"):
                    self.assertIn(
                        "salt",
                        product_info.nutrition,
                        msg=f"salt conversion missing for {case['name']}",
                    )

                if "warning_count" in expected:
                    warnings = sum(1 for log in logs if log.level == "warning")
                    rule = expected["warning_count"]
                    if callable(rule):
                        self.assertTrue(rule(warnings), msg=f"warning rule failed for {case['name']}: {warnings}")
                    else:
                        self.assertEqual(rule, warnings)

                # Ensure parse never raises and returns ProductInfo
                self.assertIsNotNone(product_info)


class ProcessInputTests(unittest.TestCase):
    def test_process_input_structure(self) -> None:
        case = TEST_CASES[0]
        result = process_input(case["input"], "text")
        self.assertTrue(result["success"])
        self.assertEqual(result["status_code"], 200)
        self.assertIn("rakuten_pc", result["html"])
        self.assertIn("product_info", result)
        self.assertIn("logs", result)

    def test_process_input_csv(self) -> None:
        csv_content = "項目名,値\n商品名,テスト商品\n名称,スイーツ\nエネルギー,120\n"
        result = process_input(csv_content, "csv")
        self.assertTrue(result["success"])
        self.assertEqual(result["product_info"].get("product_name"), "テスト商品")
        self.assertGreater(len(result["logs"]), 0)
    def test_process_input_dangerous_html_returns_400(self) -> None:
        result = process_input("<script>alert(1)</script>", "text")
        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 400)




if __name__ == "__main__":
    unittest.main()
