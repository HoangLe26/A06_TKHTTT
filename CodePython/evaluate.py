"""Print a repeatable small evaluation, including a known price-filter limitation."""

if __package__:
    from .main import build_ui
else:
    from main import build_ui


def main():
    ui = build_ui()
    cases = [
        ('text', 'black shoes', 1),
        ('text', 'red t-shirt', 6),
        ('text', 'brown backpack', 8),
        ('text', 'white sneakers', 9),
        ('voice', 'find running shoes', 1),
        ('voice', 'find black leather bag', 3),
        ('image', [0.90, 0.10, 0.20], 1),
        ('image', [0.12, 0.20, 0.93], 3),
        ('image', [0.20, 0.90, 0.15], 6),
        ('text', 'zzznomatchingproductzzz', None),
        # An intentional failure: the keyword baseline does not parse price limits.
        ('text', 'Nike shoes under 100 dollars', 5),
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
