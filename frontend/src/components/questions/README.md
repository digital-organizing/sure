# Question Components

Diese Komponenten verwalten verschiedene Fragetypen für das Client-Formular.

## Komponenten-Architektur

### `ClientQuestion.vue` (Delegator)

Die Hauptkomponente, die basierend auf dem Frageformat und den verfügbaren Optionen die richtige Unterkomponente auswählt.

### Fragetyp-Komponenten

- **`SingleChoiceQuestion.vue`** - Einfache Radio-Button-Auswahl
- **`SingleChoiceDropdownQuestion.vue`** - Radio-Button mit zusätzlichem Dropdown für Optionen mit `choices`
- **`MultipleChoiceQuestion.vue`** - Mehrfachauswahl mit Checkboxen
- **`SingleChoiceTextQuestion.vue`** - Radio-Button mit optionalem Textfeld
- **`MultipleChoiceTextQuestion.vue`** - Checkboxen mit optionalen Textfeldern
- **`OpenTextQuestion.vue`** - Reines Textfeld

## Gemeinsame Funktionalität

### `useQuestionAnswer.ts` Composable

Verwaltet die Synchronisation zwischen Komponenten und dem Pinia Store:

- Automatische Initialisierung von Antworten im Store
- Reaktive Verbindung zwischen Komponenten-Zustand und Store
- Einheitliche Update-Funktionen

## Verwendung

```vue
<ClientQuestion :question="questionSchema" />
```

Die Komponente:

1. Bestimmt automatisch den passenden Fragetyp
2. Synchronisiert Antworten mit dem `userAnswersStore`
3. Stellt eine `getClientAnswer()` Methode zur Verfügung

## Store-Integration

Alle Komponenten verwenden den `userAnswersStore` über das `useQuestionAnswer` Composable:

```typescript
const answer = computed<ClientAnswerSchema>({
  get() {
    return answersStore.getAnswerForQuestion(question.id!)
  },
  set(newAnswer) {
    answersStore.setAnswerForQuestion(question.id!, newAnswer)
  },
})
```

## Best Practices

1. Jede Fragetyp-Komponente ist eigenständig und wiederverwendbar
2. Geteilte Logik wird über Composables bereitgestellt
3. Automatic Store-Synchronisation über `watch` und `computed`
4. Konsistente API mit `getAnswer()` Methode
5. TypeScript für Typsicherheit
