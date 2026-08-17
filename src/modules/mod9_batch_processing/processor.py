# ------------------------------------------------------------------ шаги
    async def _process_one(self, video: Dict[str, Any], folder_id: int) -> None:
        """Обрабатывает одно видео: ingest → анализ → паттерны → монтаж → экспорт.

        Каждый шаг выполняется с graceful fallback: если модуль недоступен или
        падает, обработка продолжается со следующими шагами, а итоговый клип
        всё равно создаётся (при полном сбое — копия исходника).
        """
        video_id = video.get("id")
        video_path = Path(video.get("file_path", ""))
        if not video_path.exists():
            raise FileNotFoundError(f"Видео не найдено: {video_path}")

        await self._broadcast(f"  🎬 Обработка видео id={video_id}: {video_path.name}")
        await self._set_video_status(video_id, "processing")

        # Шаг 1: Ingest (нормализация). Graceful fallback — анализ продолжится по исходнику.
        await self._broadcast("    📥 Ingest...")
        ingest_result = await self._run_ingest(video_path)

        # Шаг 2: Многослойный анализ. Graceful fallback — пустой анализ.
        await self._broadcast("    🔍 Анализ...")
        analysis = await self._run_analysis(video_path, video_id)

        # Шаг 3: Поиск паттернов (самообучение). Fallback — None.
        await self._broadcast("    🧠 Паттерны...")
        pattern_profile = await self._find_pattern(video_id)

        # Шаг 4: Сторибилдер + золотые моменты. Fallback — линейная структура.
        await self._broadcast("    📖 Нарратив...")
        story = await self._build_story(video_path, analysis, pattern_profile)

        # Шаг 5: Монтаж + экспорт (через основной пайплайн). Fallback — копия.
        await self._broadcast("    ✂️ Монтаж и экспорт...")
        output_path = await self._run_editing(video_path, story)

        await self._set_video_status(video_id, "completed")
        await self._broadcast(f"    ✅ Готово: {output_path}")

    async def _run_ingest(self, video_path: Path) -> Dict[str, Any]:
        """Нормализация видео через mod0_ingest.

        Graceful fallback: при любой ошибке возвращает исходный путь,
        чтобы последующие шаги продолжили работу.
        """
        try:
            from src.modules.mod0_ingest import VideoIngest0, build_ingest_config
            from src.core.config_loader import load_config

            config = load_config()
            ingest = VideoIngest0(self.work_dir, build_ingest_config(config))
            result = await ingest.process_video(video_path)
            if result.get("success"):
                return result
            await self._broadcast(f"    ⚠️  Ingest не удался: {result.get('error', 'unknown')}")
            return {"success": False, "meta": {}, "normalized_path": str(video_path)}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ingest упал (%s), продолжаю с исходником", exc)
            await self._broadcast(f"    ⚠️  Ingest fallback: {exc}")
            return {"success": False, "meta": {}, "normalized_path": str(video_path)}

    async def _run_analysis(self, video_path: Path, video_id: int) -> Dict[str, Any]:
        """Многослойный анализ через mod8_analysis.

        Graceful fallback: при недоступности модуля возвращает пустой анализ.
        """
        try:
            from src.modules.mod8_analysis.analyzer import MultiLayerAnalyzer

            analyzer = MultiLayerAnalyzer()
            result = await analyzer.analyze(video_path, video_id=video_id)
            return result.model_dump()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Анализ упал (%s), использую пустой результат", exc)
            await self._broadcast(f"    ⚠️  Анализ fallback: {exc}")
            return {
                "emotions": [],
                "objects": [],
                "motion": [],
                "golden_moments": [],
                "duration": 0,
                "layers_status": {"error": str(exc)},
            }

    async def _find_pattern(self, video_id: int) -> Optional[Dict[str, Any]]:
        """Поиск подходящего паттерна самообучения для видео."""
        try:
            from src.modules.mod7_learning.learner import LearningEngine

            engine = LearningEngine()
            profile = engine.get_category_profile(self.category)
            if profile is not None:
                return profile.serialize()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Паттерны недоступны: %s", exc)
        return None

    async def _build_story(
        self,
        video_path: Path,
        analysis: Dict[str, Any],
        pattern_profile: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Строит нарратив, используя золотые моменты.

        Graceful fallback: при недоступности сторибилдера возвращает None —
        далее используется линейная структура (все фрагменты).
        """
        try:
            from src.utils.story_builder import build_story

            golden = analysis.get("golden_moments", [])
            fragments = [{
                "index": 1,
                "path": str(video_path),
                "filename": video_path.name,
                "duration": analysis.get("duration", 0),
            }]
            return await build_story(
                fragments,
                style_profile=pattern_profile,
                golden_moments=golden,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Сторибилдер недоступен: %s", exc)
            return None

    async def _run_editing(
        self, video_path: Path, story: Optional[Dict[str, Any]]
    ) -> str:
        """
        Реальный монтаж видео через VideoPipeline (модули mod1..mod6).

        Использует тот же полный конвейер, что и run_pipeline, но для одного
        видео. При сбое — graceful fallback на копирование исходника.
        """
        output = self.output_dir / f"{video_path.stem}_clip.mp4"
        try:
            from src.core.config_loader import load_config
            from src.core.pipeline import VideoPipeline

            config = load_config()
            pipeline = VideoPipeline(config)
            output_files = await pipeline.process_batch(
                [video_path],
                style_profile=None,
                category=self.category,
            )
            if output_files:
                await self._broadcast(f"    🎬 Клип смонтирован: {output_files[0].name}")
                return str(output_files[0])
            logger.warning("Пайплайн вернул пустой результат для %s", video_path.name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Реальный монтаж не удался (%s), fallback-копия", exc)
            await self._broadcast(f"    ⚠️  Монтаж fallback: {exc}")

        # Fallback: копируем исходник в output, чтобы не ронять задачу.
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(video_path), str(output))
            await self._broadcast(f"    🎬 Клип сохранён (копия): {output.name}")
            return str(output)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Экспорт (fallback-копия) не удался: %s", exc)
            return str(video_path)