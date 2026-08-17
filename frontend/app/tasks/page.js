<h1 className="mb-2 text-neon-gradient font-display text-4xl font-bold">
        Задачи
      </h1>
      <p className="mb-6 max-w-2xl text-sm text-[var(--text-muted)]">
        Создание клипов из исходников: загрузите видео (папка на сервере, файлы
        с ПК или ссылки) и запустите обработку. Каждое видео пройдёт полный
        пайплайн: ingest → анализ → поиск паттернов → сторибилдер → монтаж → экспорт.
      </p>

      <Card title="Загрузка исходников" subtitle="Создать новую пакетную задачу для монтажа клипов">
        <UploadFolderForm onCreated={() => setTimeout(loadTasks, 500)} />
      </Card>