# cubest — TODO

## In progress / next up

- [ ] **Сгенерировать `examples/` для каждого кейса** — папка со скилом должна
      включать самодостаточные примеры: `.sh` запускающий скрипт, реальные
      входные данные (мини-репо / нарезка nginx-лога / фейковый CSV), и
      ожидаемый результат (stdout snapshot + сгенерированный HTML).
      Структура:
      ```
      examples/
        01-file-tree/             {run.sh, sample/, expected.txt}
        02-nginx-access-log/      {run.sh, access.log.gz, expected.txt, out.html}
        03-loc-counter/           {run.sh, sample-repo/, expected.md}
        04-call-graph/            {run.sh, src/, out.svg, out.html}
        05-csv-to-echarts/        {run.sh, ads.csv, out.html}
        06-frontend-geoip/        {run.sh, enriched.log, out.html}
        07-mr-impact/             {run.sh, diff.txt, expected.md}
        08-disk-usage/            {run.sh, expected.txt}
        09-sdd-inventory/         {run.sh, sample-specs/, expected.md}
        10-k8s-resources/         {run.sh, sample-chart/, expected.md}
      ```
      Каждый `run.sh` — минимальный воспроизводимый пайплайн, ожидаемый
      результат — файлы для diff-регресс-теста.

## Nice-to-have (не блокирующее)

- [ ] Нейминг: выбрать финальное имя (см. итоги brand-name-checker;
      кандидаты: Grokdex / Slicecraft).
- [ ] Изучить README-описания похожих проектов (LogScraper, xogs, grepby)
      — вытянуть удачные формулировки use cases для собственного README.
- [ ] `format: html` без ECharts — простой standalone dashboard на голом
      Canvas / SVG (для сред без внешнего CDN).
- [ ] Preset `xml_native` через `xml.etree` — точный parse XPath-like
      выражений вместо regex по тегам.
- [ ] Streaming CSV режим для файлов > 1 GB (сейчас batch-only).
- [ ] Точный t-digest вместо reservoir sampling для percentile-мер
      (опционально, при `pip install tdigest`).
- [ ] `--diff` режим: сравнить два cube и вывести delta (для CI-регрессий
      «сколько добавилось TODO в этом PR»).
- [ ] Готовые github-actions / gitlab-ci сниппеты в `examples/ci/`.
