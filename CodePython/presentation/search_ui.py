"""Console presentation; storage access belongs to the injected services."""


class SearchUI:
    def __init__(self, query_service, speech_service, search_service, ranking_service):
        self.query_service = query_service
        self.speech_service = speech_service
        self.search_service = search_service
        self.ranking_service = ranking_service

    def display_results(self, results, top_k=None, score_label="score"):
        """Print products with their ranking scores and optional display limit."""
        if not results:
            print("No products found.")
            return

        displayed = results if top_k is None else results[:top_k]
        for position, (product, score) in enumerate(displayed, start=1):
            print(f"{position}. {product['name']}")
            print(
                f"   category: {product['category']} | color: {product['color']}"
                f" | price: {product['price']} | stock: {product['stock']}"
                f" | {score_label}: {score:.4f}"
            )

    def _retrieve_rank_display(self, query, top_k=None, score_label="score"):
        candidates = self.search_service.search(query)
        results = self.ranking_service.rank(candidates, top_k=top_k)
        self.display_results(results, score_label=score_label)
        return results

    def search_text(self, text, top_k=None):
        print("\n=== TEXT SEARCH ===")
        print("Processing mode: Text")
        print("Input:", text)
        try:
            query = self.query_service.text_query(text)
            return self._retrieve_rank_display(query, top_k=top_k)
        except (ValueError, TypeError) as exc:
            print(f"Validation error: {exc}")
            return []

    def search_voice(self, audio_input, top_k=None):
        print("\n=== VOICE SEARCH ===")
        print("Processing mode: Voice (simulated speech-to-text)")
        print("Voice input:", audio_input)
        try:
            text = self.speech_service.transcribe(audio_input)
            print("Transcribed text:", text)
            query = self.query_service.voice_query(text)
            return self._retrieve_rank_display(query, top_k=top_k)
        except (ValueError, TypeError) as exc:
            print(f"Validation error: {exc}")
            return []

    def search_image(self, embedding, top_k=None):
        print("\n=== IMAGE SEARCH ===")
        print("Processing mode: Image (artificial embedding; cosine similarity)")
        print("Query embedding:", embedding)
        try:
            query = self.query_service.image_query(embedding)
            return self._retrieve_rank_display(query, top_k=top_k, score_label="similarity")
        except (ValueError, TypeError) as exc:
            print(f"Validation error: {exc}")
            return []
