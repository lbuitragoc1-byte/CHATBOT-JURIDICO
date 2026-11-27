import re
import unicodedata
import numpy as np


class Retriever:

    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

        self.chunks = []
        self.vectors = None
        self.tokens = []

    # ========================================================
    # 1. NORMALIZACION
    # ========================================================

    def normalize(self, text):

        text = unicodedata.normalize("NFD", str(text).lower())

        text = "".join(
            char for char in text
            if unicodedata.category(char) != "Mn"
        )

        return text

    # ========================================================
    # 2. TOKENIZACION
    # ========================================================

    def tokenize(self, text):

        text = self.normalize(text)

        return re.findall(r"\b[a-z0-9]+\b", text)

    # ========================================================
    # 3. IDENTIFICACION DE NORMAS JURIDICAS
    # ========================================================

    def extract_norm_mentions(self, text):
        """
        Devuelve todas las normas explicitas encontradas y sus posiciones.
        Las posiciones permiten asociar cada articulo con la norma cercana.
        """

        normalized = self.normalize(text)
        normalized = normalized.replace("_", " ")
        normalized = re.sub(r"[/\\]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        mentions = []

        # Codigo Sustantivo del Trabajo
        cst_pattern = re.compile(
            r"\bcodigo\s+sustantivo\s+(?:del\s+)?trabajo\b|\bcst\b"
        )

        for match in cst_pattern.finditer(normalized):
            mentions.append({
                "start": match.start(),
                "end": match.end(),
                "norm": "codigo_sustantivo_trabajo"
            })

        # Leyes, decretos y resoluciones
        norm_pattern = re.compile(
            r"\b(ley|decreto(?:\s+ley)?|resolucion)\s+"
            r"(\d+)\s*(?:de\s+)?(\d{4})\b"
        )

        for match in norm_pattern.finditer(normalized):
            norm_type = match.group(1).replace(" ", "_")
            number = match.group(2)
            year = match.group(3)

            mentions.append({
                "start": match.start(),
                "end": match.end(),
                "norm": f"{norm_type}_{number}_{year}"
            })

        # Otros codigos conocidos
        code_patterns = {
            "codigo_civil": r"\bcodigo\s+civil\b",
            "codigo_penal": r"\bcodigo\s+penal\b",
            "codigo_de_comercio": r"\bcodigo\s+de\s+comercio\b",
            "codigo_general_del_proceso":
                r"\bcodigo\s+general\s+del\s+proceso\b"
        }

        for norm_name, pattern in code_patterns.items():
            for match in re.finditer(pattern, normalized):
                mentions.append({
                    "start": match.start(),
                    "end": match.end(),
                    "norm": norm_name
                })

        # Ordenar por aparicion y eliminar menciones duplicadas.
        mentions.sort(key=lambda item: (item["start"], item["end"]))

        unique_mentions = []
        seen = set()

        for mention in mentions:
            key = (mention["start"], mention["end"], mention["norm"])
            if key not in seen:
                seen.add(key)
                unique_mentions.append(mention)

        return unique_mentions

    def extract_norm_references(self, text):
        """Devuelve todas las normas identificadas, sin repetirlas."""

        references = []

        for mention in self.extract_norm_mentions(text):
            norm = mention["norm"]

            if norm not in references:
                references.append(norm)

        return references

    def extract_norm_reference(self, text):
        """
        Metodo de compatibilidad: devuelve la primera norma encontrada.
        Para busquedas con varias normas se utiliza extract_norm_references.
        """

        references = self.extract_norm_references(text)

        return references[0] if references else None

    def extract_article_norm_pairs(self, question):
        """
        Asocia cada articulo mencionado con la norma explicita mas cercana.

        Ejemplo:
        'articulo 24 del CST y articulo 33 de la Ley 100 de 1993'
        produce:
        [('24', 'codigo_sustantivo_trabajo'),
         ('33', 'ley_100_1993')]
        """

        normalized = self.normalize(question)
        article_mentions = []

        article_pattern = re.compile(
            r"\b(?:articulos?|arts?\.?)\s*(\d+[a-z]?)\b"
        )

        list_pattern = re.compile(
            r"\s*(?:,|y|e)\s*(\d+[a-z]?)\b"
        )

        for match in article_pattern.finditer(normalized):
            article_mentions.append({
                "article": match.group(1).lower(),
                "start": match.start(1),
                "end": match.end(1)
            })

            # Capturar listas: articulos 23, 24 y 25.
            cursor = match.end()

            while True:
                list_match = list_pattern.match(normalized, cursor)

                if not list_match:
                    break

                article_mentions.append({
                    "article": list_match.group(1).lower(),
                    "start": list_match.start(1),
                    "end": list_match.end(1)
                })

                cursor = list_match.end()

        norm_mentions = self.extract_norm_mentions(question)

        if not article_mentions or not norm_mentions:
            return []

        pairs = []

        for article in article_mentions:

            # Si solo se menciona una norma, se aplica a todos
            # los articulos de la pregunta.
            if len(norm_mentions) == 1:
                selected_norm = norm_mentions[0]["norm"]

            else:
                # Asociar el articulo con la mencion normativa
                # mas cercana, antes o despues de su numero.
                def distance(mention):
                    if mention["start"] >= article["end"]:
                        return mention["start"] - article["end"]

                    if mention["end"] <= article["start"]:
                        return article["start"] - mention["end"]

                    return 0

                selected_mention = min(
                    norm_mentions,
                    key=distance
                )
                selected_norm = selected_mention["norm"]

            pair = (article["article"], selected_norm)

            if pair not in pairs:
                pairs.append(pair)

        return pairs

    # ========================================================
    # 4. IDENTIFICACION DE NORMA EN LOS DOCUMENTOS
    # ========================================================

    def detect_chunk_norm(self, chunk):

        # Buscar primero metadatos especificos de la norma

        metadata_fields = [
            "norm",
            "document_norm",
            "document",
            "source"
        ]

        for field in metadata_fields:

            value = chunk.get(field)

            if not value:
                continue

            detected_norm = self.extract_norm_reference(
                str(value)
            )

            if detected_norm:
                return detected_norm

        return None

    # ========================================================
    # 5. INDEXACION DE DOCUMENTOS
    # ========================================================

    def index(self, chunks):

        self.chunks = chunks

        if not chunks:

            self.vectors = None
            self.tokens = []

            return

        texts = [
            chunk["text"]
            for chunk in chunks
        ]

        self.vectors = self.model.encode(
            texts,
            normalize_embeddings=True
        )

        self.tokens = [
            set(self.tokenize(text))
            for text in texts
        ]

    # ========================================================
    # 6. IDENTIFICACION DE ARTICULOS
    # ========================================================

    def extract_article_numbers(self, question):
        """
        Extrae uno o varios numeros de articulo mencionados
        en la pregunta.

        Admite, por ejemplo:
        - articulo 23
        - articulos 23 y 24
        - articulos 23, 24 y 25
        - articulo 23 del CST y articulo 24
        """

        normalized = self.normalize(question)

        pattern = re.compile(
            r"\b(?:articulos?|arts?\.?)\s*(\d+[a-z]?)\b"
        )

        article_numbers = []

        for match in pattern.finditer(normalized):

            first_number = match.group(1).lower()

            if first_number not in article_numbers:
                article_numbers.append(first_number)

            # Capturar listas como "articulos 23, 24 y 25".
            remaining_text = normalized[match.end():]

            list_match = re.match(
                r"(?:\s*(?:,|y|e)\s*(\d+[a-z]?))+",
                remaining_text
            )

            if list_match:

                additional_numbers = re.findall(
                    r"(?:,|y|e)\s*(\d+[a-z]?)",
                    list_match.group(0)
                )

                for number in additional_numbers:

                    number = number.lower()

                    if number not in article_numbers:
                        article_numbers.append(number)

        return article_numbers

    def extract_article_number(self, question):
        """
        Metodo de compatibilidad: devuelve el primer articulo
        encontrado, como hacia la version anterior.
        """

        article_numbers = self.extract_article_numbers(question)

        return article_numbers[0] if article_numbers else None


    # ========================================================
    # 7. BUSQUEDA Y RECUPERACION
    # ========================================================

    def search(self, question, k=5):

        if self.vectors is None:
            return []

        normalized_question = self.normalize(question)

        # ----------------------------------------------------
        # 7.1 IDENTIFICAR ARTICULO Y NORMA SOLICITADA
        # ----------------------------------------------------

        article_numbers = self.extract_article_numbers(
            question
        )

        requested_norms = self.extract_norm_references(
            question
        )

        article_norm_pairs = self.extract_article_norm_pairs(
            question
        )

        # ----------------------------------------------------
        # 7.2 FILTRAR POR UNA O VARIAS NORMAS JURIDICAS
        # ----------------------------------------------------

        candidate_indices = list(
            range(len(self.chunks))
        )

        if requested_norms:

            requested_norm_set = set(requested_norms)

            norm_indices = [
                i
                for i, chunk in enumerate(self.chunks)
                if self.detect_chunk_norm(chunk) in requested_norm_set
            ]

            # No utilizar documentos de otras normas cuando
            # el usuario especifica una o varias normas concretas.

            if not norm_indices:
                return []

            candidate_indices = norm_indices

        # ----------------------------------------------------
        # 7.3 FILTRAR POR ARTICULO Y NORMA CORRESPONDIENTE
        # ----------------------------------------------------

        if article_numbers:

            if article_norm_pairs:
                requested_pairs = set(article_norm_pairs)

                exact_article_indices = [
                    i
                    for i in candidate_indices
                    if (
                        str(self.chunks[i].get("article", "")).strip().lower(),
                        self.detect_chunk_norm(self.chunks[i])
                    ) in requested_pairs
                ]

            else:
                requested_articles = {
                    str(number).strip().lower()
                    for number in article_numbers
                }

                exact_article_indices = [
                    i
                    for i in candidate_indices
                    if str(
                        self.chunks[i].get("article", "")
                    ).strip().lower() in requested_articles
                ]

            # Si los articulos solicitados no existen dentro
            # de las normas identificadas, no recuperar otros.

            if not exact_article_indices:
                return []

            candidate_indices = exact_article_indices

        # ----------------------------------------------------
        # 7.4 BUSQUEDA SEMANTICA
        # ----------------------------------------------------

        query_vector = self.model.encode(
            [question],
            normalize_embeddings=True
        )[0]

        semantic_scores = (
            np.asarray(self.vectors)
            @ np.asarray(query_vector)
        )

        # ----------------------------------------------------
        # 7.5 BUSQUEDA LEXICA
        # ----------------------------------------------------

        question_tokens = set(
            self.tokenize(question)
        )

        stopwords = {
            "que", "como", "cual", "cuales", "los", "las",
            "del", "de", "la", "el", "un", "una", "en",
            "por", "para", "con", "sobre", "segun", "es",
            "son", "se", "y", "o", "al", "lo"
        }

        question_tokens -= stopwords

        lexical_scores = []

        for document_tokens in self.tokens:

            if not question_tokens:

                lexical_scores.append(0.0)

                continue

            matches = question_tokens.intersection(
                document_tokens
            )

            lexical_scores.append(
                len(matches) / len(question_tokens)
            )

        lexical_scores = np.asarray(lexical_scores)

        # Coincidencia entre la pregunta y el titulo del articulo.
        heading_scores = []

        # ----------------------------------------------------
        # 7.6 IDENTIFICAR TIPO DE CONSULTA
        # ----------------------------------------------------

        asks_references = any(
            term in normalized_question
            for term in [
                "concordancias",
                "notas de vigencia",
                "doctrina",
                "jurisprudencia"
            ]
        )

        asks_history = any(
            term in normalized_question
            for term in [
                "historico",
                "historica",
                "legislacion anterior",
                "texto original",
                "version original",
                "texto anterior",
                "version anterior",
                "version previa",
                "redaccion anterior",
                "antes de la modificacion",
                "antes de la reforma"
            ]
        )

        asks_original = any(
            term in normalized_question
            for term in [
                "texto original",
                "version original",
                "redaccion original",
                "codigo sustantivo original"
            ]
        )

        # Detectar preguntas que solicitan comparar dos o mas versiones.
        asks_comparison = any(
            term in normalized_question
            for term in [
                "comparar",
                "comparacion",
                "comparativo",
                "diferencia",
                "diferencias",
                "frente a",
                "versus"
            ]
        ) or bool(re.search(r"\bvs\.?\b", normalized_question))

        # Detectar si la consulta solicita el texto o la norma vigente/actual.
        asks_current = any(
            term in normalized_question
            for term in [
                "texto vigente",
                "version vigente",
                "texto actual",
                "version actual",
                "norma vigente",
                "normativa vigente",
                "legislacion vigente",
                "redaccion vigente",
                "vigencia actual",
                "vigente",
                "actualmente"
            ]
        )

        # Identificar las versiones normativas expresamente mencionadas.
        # Ejemplo: "L del codigo",
        #"codigoey 50 de 1990" -> "ley_50_1990".
        requested_versions = set()

        if asks_original:
            requested_versions.add("codigo_sustantivo_original")

        version_pattern = re.compile(
            r"\b(ley|decreto(?:\s+ley)?)\s+"
            r"(\d+)\s*(?:de\s+)?(\d{4})\b"
        )

        for version_match in version_pattern.finditer(normalized_question):
            norm_type = version_match.group(1).replace(" ", "_")
            requested_versions.add(
                f"{norm_type}_{version_match.group(2)}_{version_match.group(3)}"
            )

        # ----------------------------------------------------
        # 7.7 CLASIFICACION Y PUNTUACION
        # ----------------------------------------------------

        final_scores = []

        requested_articles = {
            str(number).strip().lower()
            for number in article_numbers
        }

        
        for i, chunk in enumerate(self.chunks):

            semantic = (
                float(semantic_scores[i]) + 1
            ) / 2

            lexical = float(lexical_scores[i])

            score = (
                0.55 * semantic +
                0.35 * lexical
            )

            text = self.normalize(
                chunk["text"]
            )

            # Extraer el titulo de la primera linea del fragmento.
            heading_line = (
                str(chunk.get("text", "")).splitlines()[0]
                if chunk.get("text")
                else ""
            )

            # Quitar etiquetas editoriales y el numero del articulo.
            heading_line = re.sub(r"<[^>]*>", " ", heading_line)
            heading_line = self.normalize(heading_line)
            heading_line = re.sub(
                r"^\s*articulo\s+\d+[a-z]?\s*\.?\s*",
                "",
                heading_line
            )

            heading_tokens = set(self.tokenize(heading_line)) - stopwords
            heading_score = (
                len(question_tokens.intersection(heading_tokens))
                / len(question_tokens)
                if question_tokens
                else 0.0
            )
            heading_scores.append(heading_score)

            # En consultas sin numero de articulo, el titulo aporta
            # una señal adicional de relevancia.
            if not article_numbers:
                score += 0.10 * heading_score

            chunk_article = str(
                chunk.get("article", "")
            ).strip().lower()

            section = chunk.get("section", "")
            version = chunk.get("version", "")

            # Bonificar coincidencias de articulos solicitados

            if article_numbers and chunk_article in requested_articles:

                has_article_heading = bool(
                    re.search(
                        r"^\s*articulo\s+"
                        + re.escape(chunk_article)
                        + r"\s*\.",
                        text
                    )
                )

                if has_article_heading:
                    score += 0.35

                # Indicadores de redaccion actualizada

                current_markers = [
                    "nuevo texto es el siguiente",
                    "literal modificado por el articulo 16 de la ley 2466 de 2025",
                    "modificado por la ley 2466 de 2025"
                ]

                if has_article_heading and any(
                    marker in text
                    for marker in current_markers
                ):
                    score += 0.50

            # Priorizar contenido normativo principal
            # para todas las preguntas, no solo las que
            # mencionan un numero de articulo.

            if section == "contenido_principal":

                score += 0.15

            # Reducir referencias editoriales cuando
            # el usuario no las esta solicitando.

            elif section in {
                "notas_vigencia",
                "concordancias",
                "doctrina"
            } and not asks_references:

                score -= 0.30

            # Reducir prioridad historica cuando
            # el usuario no solicita versiones anteriores.

            if (
                not asks_history
                and (
                    section == "legislacion_anterior"
                    or version == "historica"
                )
            ):

                score -= 0.50

            final_scores.append(score)



        # 7.8 FILTRAR VERSIONES HISTORICAS Y SECCIONES
        # ----------------------------------------------------

        requested_targets = (
            article_norm_pairs
            if article_norm_pairs
            else [(number, None) for number in article_numbers]
        )

        if article_numbers:

            filtered_indices = []

            # Aplicar los filtros por articulo y, cuando se conozca,
            # por la norma juridica a la que pertenece.

            for requested_article, requested_norm in requested_targets:

                article_indices = [
                    i
                    for i in candidate_indices
                    if (
                        str(self.chunks[i].get("article", "")).strip().lower()
                        == requested_article.lower()
                        and (
                            requested_norm is None
                            or self.detect_chunk_norm(self.chunks[i]) == requested_norm
                        )
                    )
                ]

                if asks_comparison:

                    # En una comparacion no debemos conservar unicamente
                    # el texto original: hay que recuperar cada version
                    # que el usuario haya mencionado expresamente.
                    comparison_indices = []

                    for requested_version in sorted(requested_versions):

                        version_indices = [
                            i
                            for i in article_indices
                            if self.chunks[i].get("version")
                            == requested_version
                        ]

                        comparison_indices.extend(version_indices)

                    # Algunos documentos identifican el texto original
                    # con la etiqueta generica "historica".
                    if asks_original:

                        original_indices = [
                            i
                            for i in article_indices
                            if self.chunks[i].get("version")
                            in {
                                "historica",
                                "codigo_sustantivo_original"
                            }
                        ]

                        comparison_indices.extend(original_indices)

                    # Si se solicita comparar con la norma actual,
                    # incluir tambien el contenido principal.
                    if asks_current:

                        current_indices = [
                            i
                            for i in article_indices
                            if self.chunks[i].get("section")
                            == "contenido_principal"
                        ]

                        comparison_indices.extend(current_indices)

                    # Si no se identificaron versiones concretas,
                    # conservar como respaldo el comportamiento historico.
                    if not comparison_indices and asks_history:

                        comparison_indices = [
                            i
                            for i in article_indices
                            if self.chunks[i].get("section")
                            == "legislacion_anterior"
                        ]

                    if comparison_indices:
                        article_indices = list(
                            dict.fromkeys(comparison_indices)
                        )

                elif asks_history:

                    historical_indices = [
                        i
                        for i in article_indices
                        if self.chunks[i].get("section")
                        == "legislacion_anterior"
                    ]

                    if asks_original:

                        original_indices = [
                            i
                            for i in historical_indices
                            if self.chunks[i].get("version")
                            in {
                                "historica",
                                "codigo_sustantivo_original"
                            }
                        ]

                        if original_indices:
                            article_indices = original_indices

                        elif historical_indices:
                            article_indices = historical_indices

                    elif historical_indices:
                        article_indices = historical_indices

                elif not asks_references:

                    principal_indices = [
                        i
                        for i in article_indices
                        if self.chunks[i].get("section")
                        == "contenido_principal"
                    ]

                    if principal_indices:
                        article_indices = principal_indices

                filtered_indices.extend(article_indices)

            # Eliminar duplicados conservando el orden.
            candidate_indices = list(dict.fromkeys(filtered_indices))


        # ----------------------------------------------------
        # 7.9 ORDENAR RESULTADOS
        # ----------------------------------------------------

        ranked_all = sorted(
            candidate_indices,
            key=lambda i: final_scores[i],
            reverse=True
        )

        if article_numbers:

            # Garantizar al menos un fragmento de cada combinacion
            # articulo-norma solicitada, siempre que exista.
            ranked_indices = []

            for requested_article, requested_norm in requested_targets:

                article_ranked = [
                    i
                    for i in ranked_all
                    if (
                        str(self.chunks[i].get("article", "")).strip().lower()
                        == requested_article.lower()
                        and (
                            requested_norm is None
                            or self.detect_chunk_norm(self.chunks[i]) == requested_norm
                        )
                    )
                ]

                if article_ranked and article_ranked[0] not in ranked_indices:
                    ranked_indices.append(article_ranked[0])

                # En preguntas comparativas, garantizar al menos un
                # fragmento de cada version solicitada.
                if asks_comparison:

                    for requested_version in sorted(requested_versions):

                        version_ranked = [
                            i
                            for i in article_ranked
                            if self.chunks[i].get("version")
                            == requested_version
                        ]

                        if (
                            version_ranked
                            and version_ranked[0] not in ranked_indices
                        ):
                            ranked_indices.append(version_ranked[0])

                    if asks_original:

                        original_ranked = [
                            i
                            for i in article_ranked
                            if self.chunks[i].get("version")
                            in {
                                "historica",
                                "codigo_sustantivo_original"
                            }
                        ]

                        if (
                            original_ranked
                            and original_ranked[0] not in ranked_indices
                        ):
                            ranked_indices.append(original_ranked[0])

                    if asks_current:

                        current_ranked = [
                            i
                            for i in article_ranked
                            if self.chunks[i].get("section")
                            == "contenido_principal"
                        ]

                        if (
                            current_ranked
                            and current_ranked[0] not in ranked_indices
                        ):
                            ranked_indices.append(current_ranked[0])

            # Completar los resultados restantes por puntuacion.
            effective_k = max(k, len(ranked_indices))

            for i in ranked_all:

                if len(ranked_indices) >= effective_k:
                    break

                if i not in ranked_indices:
                    ranked_indices.append(i)

        else:

            ranked_indices = ranked_all[:k]

            # Si el titulo coincide claramente con la pregunta,
            # priorizar los fragmentos del contenido principal de ese articulo.
            principal_heading_indices = [
                i
                for i in candidate_indices
                if (
                    self.chunks[i].get("section") == "contenido_principal"
                    and self.chunks[i].get("article") is not None
                    and heading_scores[i] >= 0.65
                )
            ]

            if principal_heading_indices:
                best_heading_index = max(
                    principal_heading_indices,
                    key=lambda i: (heading_scores[i], final_scores[i])
                )

                best_chunk = self.chunks[best_heading_index]
                best_article = str(best_chunk.get("article", "")).strip().lower()
                best_norm = self.detect_chunk_norm(best_chunk)
                best_version = best_chunk.get("version")
                best_source = str(
                    best_chunk.get("source")
                    or best_chunk.get("document")
                    or best_chunk.get("filename")
                    or ""
                )

                focused_indices = [
                    i
                    for i in principal_heading_indices
                    if (
                        str(self.chunks[i].get("article", "")).strip().lower()
                        == best_article
                        and self.detect_chunk_norm(self.chunks[i]) == best_norm
                        and self.chunks[i].get("version") == best_version
                        and str(
                            self.chunks[i].get("source")
                            or self.chunks[i].get("document")
                            or self.chunks[i].get("filename")
                            or ""
                        ) == best_source
                    )
                ]

                focused_indices.sort(
                    key=lambda i: final_scores[i],
                    reverse=True
                )

                # Mantener k resultados, colocando primero las partes
                # del articulo que coincide con el tema consultado.
                ranked_indices = focused_indices[:k]

                for i in ranked_all:
                    if len(ranked_indices) >= k:
                        break
                    if i not in ranked_indices:
                        ranked_indices.append(i)

        # ----------------------------------------------------
        # 7.10 CONSTRUIR RESULTADOS
        # ----------------------------------------------------

        results = []

        for index in ranked_indices:

            result = dict(
                self.chunks[index]
            )

            result["score"] = float(
                final_scores[index]
            )

            result["semantic_score"] = float(
                semantic_scores[index]
            )

            result["lexical_score"] = float(
                lexical_scores[index]
            )

            result["heading_score"] = float(
                heading_scores[index]
            )

            results.append(result)


        print("\n========== DIAGNÓSTICO DE RECUPERACIÓN ==========")

        for position, result in enumerate(results, start=1):

            print(
                f"\nRESULTADO {position}"
                f"\nPuntuación total: {result['score']:.4f}"
                f"\nPuntuación semántica: {result['semantic_score']:.4f}"
                f"\nPuntuación léxica: {result['lexical_score']:.4f}"
                f"\nCoincidencia con título: {result['heading_score']:.4f}"
                f"\nArtículo: {result.get('article')}"
                f"\nSección: {result.get('section')}"
                f"\nVersión: {result.get('version')}"
                f"\nTexto: {result.get('text', '')[:250]}"
            )

        print("\n=================================================\n")


        return results
