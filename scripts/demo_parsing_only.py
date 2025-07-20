#!/usr/bin/env python3
"""
Демонстрация парсинга транскрипта без GUI.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def parse_manual_transcript(text):
    """Parse manually entered transcript text into fragments."""
    fragments = []
    lines = text.split('\n')
    current_time = 0
    current_text = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if line looks like a timestamp (e.g., "0:00", "1:23", "12:34")
        if ':' in line and len(line.split(':')) == 2:
            try:
                time_parts = line.split(':')
                minutes = int(time_parts[0])
                seconds = int(time_parts[1])
                timestamp = minutes * 60 + seconds
                
                # Save previous fragment if exists
                if current_text:
                    fragments.append({
                        'start': current_time,
                        'text': current_text.strip()
                    })
                
                # Start new fragment
                current_time = timestamp
                current_text = ""
                continue
            except ValueError:
                pass
        
        # Add line to current text
        if current_text:
            current_text += " " + line
        else:
            current_text = line
    
    # Add final fragment
    if current_text:
        fragments.append({
            'start': current_time,
            'text': current_text.strip()
        })
    
    # If no timestamps were found, treat entire text as one fragment
    if not fragments and text:
        fragments.append({
            'start': 0,
            'text': text
        })
    
    return fragments

def estimate_duration_from_fragments(fragments):
    """Estimate video duration from transcript fragments."""
    if not fragments:
        return 0
    
    # Find the last timestamp and add estimated duration for last fragment
    last_fragment = fragments[-1]
    last_start = last_fragment.get('start', 0)
    
    # Estimate duration based on text length (rough approximation)
    last_text = last_fragment.get('text', '')
    estimated_last_duration = len(last_text.split()) * 0.5  # ~0.5 seconds per word
    
    return last_start + estimated_last_duration

def demo_parsing():
    """Демонстрация парсинга транскрипта."""
    
    # Пример транскрипта скейт-видео
    sample_transcript = """0:00
привет всем меня зовут Макс и сегодня я покажу вам как делать kickflip
0:10
сначала нужно правильно поставить ноги на доску
0:20
передняя нога должна быть примерно в середине доски
0:30
а задняя нога на тейле вот так
0:45
теперь самое главное это движение
1:00
делаем олли и одновременно поворачиваем доску пальцем передней ноги
1:30
вот смотрите как это выглядит
2:00
попробуйте сами несколько раз
2:15
не расстраивайтесь если не получается с первого раза
2:30
это нормально для такого сложного трюка
2:45
продолжайте тренироваться и у вас обязательно получится
3:00
увидимся в следующем видео удачи"""

    print("=== ДЕМОНСТРАЦИЯ ПАРСИНГА РУЧНОГО ТРАНСКРИПТА ===\n")
    
    # Парсим тестовый транскрипт
    print("1. Парсинг транскрипта...")
    fragments = parse_manual_transcript(sample_transcript)
    print(f"   Найдено фрагментов: {len(fragments)}")
    
    # Показываем все фрагменты
    print("\n2. Все фрагменты:")
    for i, fragment in enumerate(fragments):
        minutes = int(fragment['start'] // 60)
        seconds = int(fragment['start'] % 60)
        print(f"   {i+1}. {minutes}:{seconds:02d} - {fragment['text']}")
    
    # Оценка длительности
    duration = estimate_duration_from_fragments(fragments)
    print(f"\n3. Оценочная длительность: {duration:.1f} секунд ({duration/60:.1f} минут)")
    
    # Анализ для поиска трюков (упрощенный)
    print("\n4. Анализ для поиска трюков:")
    print("   Ищем фрагменты с короткими текстами (возможные трюки)...")
    
    potential_tricks = []
    for i, fragment in enumerate(fragments):
        word_count = len(fragment['text'].split())
        if word_count <= 8:  # Короткие фразы могут указывать на трюки
            potential_tricks.append((fragment, word_count))
    
    if potential_tricks:
        print(f"   Найдено потенциальных трюков: {len(potential_tricks)}")
        for fragment, word_count in potential_tricks:
            minutes = int(fragment['start'] // 60)
            seconds = int(fragment['start'] % 60)
            print(f"   - {minutes}:{seconds:02d}: {fragment['text']} ({word_count} слов)")
    else:
        print("   Потенциальные трюки не найдены (все фрагменты содержат много текста)")
    
    print("\n=== ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА ===")
    print("\nВ реальном приложении этот парсинг используется для:")
    print("- Создания структуры данных совместимой с автоматическими транскриптами")
    print("- Анализа трюков через video_processor.extract_trick_segments()")
    print("- Создания саммари через summarizer")
    print("- Скачивания видео сегментов")

if __name__ == "__main__":
    demo_parsing()