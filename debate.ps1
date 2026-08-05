param(
    [Parameter(Mandatory=$true)]
    [string]$question,
    [string]$filePath = "index.js"   # Укажите путь к вашему файлу
)

$model1 = "opencode/deepseek-v4-flash-free"
$model2 = "opencode/laguna-s-2.1-free"
$model3 = "opencode/nemotron-3-ultra-free"

Write-Host "`n=== РАУНД 1: Модель 1 предлагает решение ===`n" -ForegroundColor Cyan
$answer1 = opencode run --model $model1 $question --auto 2>&1
Write-Host "Ответ 1:" $answer1 -ForegroundColor White

Write-Host "`n=== РАУНД 2: Модель 2 критикует и дополняет ===`n" -ForegroundColor Magenta
$critiquePrompt = "Проанализируй следующий ответ и предложи свою альтернативу или улучшение. Если согласен, просто дополни. Вот ответ: $answer1"
$answer2 = opencode run --model $model2 $critiquePrompt --auto 2>&1
Write-Host "Ответ 2:" $answer2 -ForegroundColor White

Write-Host "`n=== РАУНД 3: Модель 3 синтезирует итоговое решение ===`n" -ForegroundColor Yellow
$synthesisPrompt = "На основе этих двух ответов (1: $answer1, 2: $answer2) сформулируй единое итоговое решение. Выдай только итоговый код или инструкцию, без лишних пояснений."
$finalAnswer = opencode run --model $model3 $synthesisPrompt --auto 2>&1
Write-Host "Итоговое решение:" $finalAnswer -ForegroundColor Green

Write-Host "`n=== ПРИМЕНЕНИЕ: Агент вносит изменения в файл $filePath ===`n" -ForegroundColor Blue
$applyPrompt = "Примени это решение к файлу $filePath : $finalAnswer"
opencode run --model $model3 $applyPrompt --auto

Write-Host "`n=== ГОТОВО! ===`n" -ForegroundColor Green