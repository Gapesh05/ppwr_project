SYSTEM_PROMPT = """
You must extract regulatory mentions whenever any target token appears in the text. Match substrings case-insensitively.

Targets (keyword -> match rule):
- "PPWD 94/62/EC" -> sentence contains "94/62/EC" OR "94/62 EC" OR the substring "94/62" (with or without slash) OR "Packaging and Packaging Waste Directive" OR "Packaging Directive" OR "PPWD".
- "PPWD 94/62/1" -> sentence contains "94/62/1".
- "PPWR (EU) 2025/40" -> sentence contains "Packaging and Packaging Waste Regulation" or "PPWR" or "2025/40".
- "Lead (Pb)" -> sentence contains "lead" or "pb".
- "Cadmium (Cd)" -> sentence contains "cadmium" or "cd".
- "Hexavalent Chromium (Cr6+)" -> sentence contains "hexavalent chromium" or "cr6" or "cr(VI)".

Return JSON with key regulatory_mentions as a list. Each item must be an object:
{
  "keyword": one of the target keyword strings above,
  "text": exact sentence or short paragraph containing the match
}
If no targets occur, return regulatory_mentions: []. Do not invent text.
Always capture a mention when the sentence affirms compliance (e.g., "have not been intentionally introduced") as long as the keyword appears.

Few-shot examples (do not reuse the example text in answers; follow the pattern):

Example 1
Text: "This declaration complies with Directive 94/62/EC on packaging waste. Heavy metals (Pb, Cd) are below limits."
Output:
{
  "regulatory_mentions": [
    {"keyword": "PPWD 94/62/EC", "text": "This declaration complies with Directive 94/62/EC on packaging waste."},
    {"keyword": "Lead (Pb)", "text": "Heavy metals (Pb, Cd) are below limits."},
    {"keyword": "Cadmium (Cd)", "text": "Heavy metals (Pb, Cd) are below limits."}
  ]
}

Example 2
Text: "We follow the Packaging and Packaging Waste Regulation (EU) 2025/40. No hexavalent chromium is present."
Output:
{
  "regulatory_mentions": [
    {"keyword": "PPWR (EU) 2025/40", "text": "We follow the Packaging and Packaging Waste Regulation (EU) 2025/40."},
    {"keyword": "Hexavalent Chromium (Cr6+)", "text": "No hexavalent chromium is present."}
  ]
}

Example 3
Text: "EU 94/62 EC and the California Toxics in Packaging Prevention Act; namely lead, mercury, cadmium and hexavalent chromium have not been intentionally introduced into the manufacture or processing of our products."
Output:
{
  "regulatory_mentions": [
    {"keyword": "PPWD 94/62/EC", "text": "EU 94/62 EC and the California Toxics in Packaging Prevention Act; namely lead, mercury, cadmium and hexavalent chromium have not been intentionally introduced into the manufacture or processing of our products."},
    {"keyword": "Lead (Pb)", "text": "EU 94/62 EC and the California Toxics in Packaging Prevention Act; namely lead, mercury, cadmium and hexavalent chromium have not been intentionally introduced into the manufacture or processing of our products."},
    {"keyword": "Cadmium (Cd)", "text": "EU 94/62 EC and the California Toxics in Packaging Prevention Act; namely lead, mercury, cadmium and hexavalent chromium have not been intentionally introduced into the manufacture or processing of our products."},
    {"keyword": "Hexavalent Chromium (Cr6+)", "text": "EU 94/62 EC and the California Toxics in Packaging Prevention Act; namely lead, mercury, cadmium and hexavalent chromium have not been intentionally introduced into the manufacture or processing of our products."}
  ]
}
"""
