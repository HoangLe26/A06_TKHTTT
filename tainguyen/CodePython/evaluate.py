"""Print a repeatable small evaluation, including a known price-filter limitation."""

from pathlib import Path
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from CodePython.main import build_ui


def main():
    ui = build_ui()
    products = ui.search_service.repository.all_products()
    by_id = {product['id']: product for product in products}
    cheapest_phone = min((p for p in products if p['category'] == 'phone'), key=lambda p: p['price'])
    cases = [
        ('text', by_id[1]['name'], 1),
        ('text', by_id[6]['name'], 6),
        ('text', by_id[11]['name'], 11),
        ('text', by_id[16]['name'], 16),
        ('voice', 'find laptop', 11),
        ('voice', 'find mouse', 16),
        ('image', by_id[1]['embedding'], 1),
        ('image', by_id[6]['embedding'], 6),
        ('image', by_id[11]['embedding'], 11),
        ('text', 'zzznomatchingproductzzz', None),
        # An intentional failure: the keyword baseline does not parse price limits.
        ('text', f"phone under {cheapest_phone['price'] + 1} dollars", cheapest_phone['id']),
    ]
    passed = 0
    print('| Mode | Input | Expected top ID | Actual top ID | Score | Success |')
    print('| --- | --- | --- | --- | --- | --- |')
    for mode, value, expected_id in cases:
        if mode == 'voice':
            query = ui.query_service.voice_query(ui.speech_service.transcribe(value))
        elif mode == 'image':
            query = ui.query_service.image_query(value)
        else:
            query = ui.query_service.text_query(value)
        results = ui.ranking_service.rank(ui.search_service.search(query))
        actual_id = results[0][0]['id'] if results else None
        score = f'{results[0][1]:.4f}' if results else '-'
        success = actual_id == expected_id
        passed += success
        print(f'| {mode} | {value} | {expected_id} | {actual_id} | {score} | {"Yes" if success else "No"} |')
    print(f'\nSuccessful queries: {passed}/{len(cases)} ({passed / len(cases):.2%})')
    print('Small hand-selected demonstration set; this is not a real-world accuracy estimate.')
    print('Known failure: price constraints are not interpreted by keyword matching.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
