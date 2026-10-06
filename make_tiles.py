"""Generate product tile SVGs into app/static/products/.

Real raster product photography isn't available offline, so each tile is a clean
vector illustration on a soft gradient — reads as a catalog image, not an emoji.
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "static", "products")
os.makedirs(OUT, exist_ok=True)

W = H = 400
BG = {"Electronics": ("#eef2ff", "#dbe4ff"), "Fashion": ("#fff1f2", "#ffe0e6"),
      "Books": ("#ecfdf5", "#d7f5e6"), "Home & Kitchen": ("#fffbeb", "#fdf0d5"),
      "Sports & Fitness": ("#eefcfb", "#d5f4f1"), "Beauty": ("#fdf2ff", "#f3ddfc")}

# (product_id, category, label, body-svg)
ITEMS = [
    ("PROD-EAR-001", "Electronics", "Earbuds", """
      <circle cx="150" cy="210" r="46" fill="#1f2937"/><circle cx="150" cy="210" r="24" fill="#4f8cff"/>
      <circle cx="250" cy="210" r="46" fill="#1f2937"/><circle cx="250" cy="210" r="24" fill="#4f8cff"/>
      <rect x="140" y="120" width="120" height="34" rx="17" fill="#374151"/>
      <rect x="160" y="128" width="80" height="18" rx="9" fill="#6b7280"/>"""),
    ("PROD-SW-002", "Electronics", "Smartwatch", """
      <rect x="150" y="90" width="100" height="220" rx="34" fill="#111827"/>
      <rect x="162" y="102" width="76" height="196" rx="26" fill="#4f8cff"/>
      <rect x="176" y="150" width="48" height="10" rx="5" fill="#e0e7ff"/>
      <rect x="176" y="172" width="34" height="10" rx="5" fill="#e0e7ff"/>
      <circle cx="200" cy="230" r="24" fill="none" stroke="#e0e7ff" stroke-width="9"/>"""),
    ("PROD-PB-003", "Electronics", "Power Bank", """
      <rect x="120" y="130" width="160" height="150" rx="20" fill="#111827"/>
      <rect x="140" y="150" width="120" height="14" rx="7" fill="#31c48d"/>
      <rect x="140" y="176" width="86" height="14" rx="7" fill="#4f8cff"/>
      <rect x="176" y="240" width="48" height="14" rx="4" fill="#6b7280"/>"""),
    ("PROD-KT-004", "Fashion", "Kurta", """
      <path d="M200 110 L150 140 L128 210 L160 220 L160 300 L240 300 L240 220 L272 210 L250 140 Z"
            fill="#d9a86c"/>
      <path d="M200 110 L182 132 L200 160 L218 132 Z" fill="#c8925a"/>
      <circle cx="200" cy="180" r="4" fill="#a97a45"/><circle cx="200" cy="210" r="4" fill="#a97a45"/>"""),
    ("PROD-CC-005", "Electronics", "Cable", """
      <path d="M150 130 C 150 250, 250 250, 250 130" fill="none" stroke="#374151"
            stroke-width="22" stroke-linecap="round"/>
      <path d="M150 130 C 150 250, 250 250, 250 130" fill="none" stroke="#6b7280"
            stroke-width="10" stroke-linecap="round" stroke-dasharray="6 8"/>
      <rect x="138" y="96" width="24" height="40" rx="6" fill="#111827"/>
      <rect x="238" y="96" width="24" height="40" rx="6" fill="#111827"/>"""),
    ("PROD-BK-006", "Books", "Book", """
      <rect x="130" y="110" width="140" height="190" rx="8" fill="#2563eb"/>
      <rect x="130" y="110" width="20" height="190" rx="8" fill="#1e40af"/>
      <rect x="166" y="150" width="86" height="10" rx="5" fill="#bfdbfe"/>
      <rect x="166" y="172" width="66" height="10" rx="5" fill="#bfdbfe"/>
      <rect x="166" y="194" width="76" height="10" rx="5" fill="#bfdbfe"/>"""),
    ("PROD-HK-007", "Home & Kitchen", "Masala Dabba", """
      <ellipse cx="200" cy="150" rx="92" ry="26" fill="#9ca3af"/>
      <path d="M108 150 L108 250 A92 26 0 0 0 292 250 L292 150 Z" fill="#cbd5e1"/>
      <ellipse cx="200" cy="150" rx="72" ry="18" fill="#e5e7eb"/>
      <circle cx="175" cy="152" r="16" fill="#f59e0b"/><circle cx="225" cy="152" r="16" fill="#ef4444"/>
      <circle cx="200" cy="176" r="16" fill="#10b981"/>"""),
    ("PROD-BT-008", "Home & Kitchen", "Bottle", """
      <rect x="168" y="100" width="64" height="34" rx="10" fill="#b45309"/>
      <path d="M160 134 L240 134 L232 300 A10 10 0 0 1 222 310 L178 310 A10 10 0 0 1 168 300 Z"
            fill="#d97706"/>
      <rect x="172" y="170" width="56" height="10" rx="5" fill="#fbbf24"/>
      <rect x="172" y="220" width="56" height="10" rx="5" fill="#fbbf24"/>"""),
    ("PROD-YM-009", "Sports & Fitness", "Yoga Mat", """
      <rect x="120" y="150" width="200" height="34" rx="17" fill="#7c3aed"/>
      <rect x="120" y="192" width="200" height="34" rx="17" fill="#a78bfa"/>
      <rect x="120" y="234" width="200" height="34" rx="17" fill="#7c3aed"/>
      <circle cx="300" cy="207" r="16" fill="#ede9fe"/>"""),
    ("PROD-FW-010", "Beauty", "Face Wash", """
      <rect x="170" y="120" width="60" height="40" rx="8" fill="#16a34a"/>
      <path d="M158 160 L242 160 L236 300 A12 12 0 0 1 224 312 L176 312 A12 12 0 0 1 164 300 Z"
            fill="#22c55e"/>
      <rect x="176" y="200" width="48" height="60" rx="8" fill="#dcfce7"/>
      <circle cx="200" cy="230" r="14" fill="#16a34a"/>"""),
]


def tile(pid, cat, label, body):
    c1, c2 = BG[cat]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{label}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#g)"/>
  <circle cx="200" cy="205" r="150" fill="#ffffff" opacity="0.55"/>
  {body.strip()}
</svg>
"""


for pid, cat, label, body in ITEMS:
    with open(os.path.join(OUT, f"{pid}.svg"), "w", encoding="utf-8") as f:
        f.write(tile(pid, cat, label, body))

print(f"wrote {len(ITEMS)} tiles -> {OUT}")
for fn in sorted(os.listdir(OUT)):
    print("  ", fn)
