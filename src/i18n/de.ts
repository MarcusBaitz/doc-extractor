/**
 * German interface copy and the vocabulary that keeps it consistent.
 *
 * Clerks see the words in the left column. The engine-room terms in the right
 * column remain in code and technical documentation, never on a user screen:
 *
 * | Auf dem Bildschirm | Im Maschinenraum |
 * |---|---|
 * | Vorlage | Dokumenttyp, Template |
 * | Angabe | Feld |
 * | Beleg | Dokument |
 * | sicher erkannt | Konfidenz ≥ Schwellwert |
 * | nicht eindeutig | Konfidenz unter Schwellwert |
 * | wartet auf Prüfung | Review-Queue |
 * | abgelegt | exportiert |
 * | Alle Belege bleiben auf diesem Gerät | Air-Gap-Modus |
 *
 * Model names, reading stages, numeric confidence, `snake_case`, JSON keys,
 * locators, provenance, bounding boxes and OCR are reserved for
 * “Einstellungen → Technische Details”. Error copy is resolved through the
 * stable RFC 9457 `key`, so sidecar wording cannot leak into the interface.
 */

export const de = {
  app: {
    title: 'Substrakt',
    version: 'Version',
    promise: 'Alle Belege bleiben auf diesem Gerät.',
  },

  places: {
    overview: 'Übersicht',
    review: 'Prüfen',
    templates: 'Vorlagen',
    settings: 'Einstellungen',
  },

  theme: {
    toggle: 'Hell oder dunkel',
  },

  keys: {
    enter: 'Enter',
  },

  time: {
    justNow: 'gerade eben',
    minuteAgo: 'vor einer Minute',
    minutesAgo: (minutes: number) => `vor ${minutes} Minuten`,
    hourAgo: 'vor einer Stunde',
    hoursAgo: (hours: number) => `vor ${hours} Stunden`,
    yesterday: 'gestern',
    daysAgo: (days: number) => `vor ${days} Tagen`,
  },

  state: {
    running: 'Alles läuft',
    starting: 'Substrakt startet',
    startingDetail: 'Einen Augenblick — das Lesewerk wird bereitgemacht.',
    unavailable: 'Substrakt läuft nicht',
    unavailableDetail: 'Bitte starten Sie die Anwendung neu.',
    ready: (templates: number) =>
      templates === 1
        ? '1 Vorlage eingerichtet'
        : `${templates} Vorlagen eingerichtet`,
    noTemplates: 'Noch keine Vorlage eingerichtet',
  },

  overview: {
    title: 'Übersicht',
    subtitle:
      'Was gelesen wurde, steht hier. Zu tun ist nur etwas, wenn eine Angabe nicht eindeutig war.',
    documents: 'Belege in dieser Sitzung',
    waiting: 'warten auf Ihre Prüfung',
    gaps: 'mit fehlender Angabe',
    reviewNow: 'Jetzt prüfen',
    recent: 'Zuletzt verarbeitet',
    lastRead: 'zuletzt gelesen',
    nothingYet: 'In dieser Sitzung wurde noch kein Beleg gelesen.',
    nothingYetDetail:
      'Richten Sie eine Vorlage ein — danach lesen Sie damit jeden weiteren Beleg derselben Art.',
    firstTemplate: 'Erste Vorlage einrichten',
    readDocument: 'Beleg lesen',
    folders: 'Überwachte Ordner',
    folderDetail:
      'Ordner werden noch nicht überwacht. Bis dahin wählen Sie jeden Beleg selbst aus — die Vorlage arbeitet gleich.',
  },

  review: {
    empty: 'Nichts zu prüfen',
    emptyDetail: 'Alle gelesenen Angaben waren eindeutig.',
    documentOf: (n: number, total: number) => `Beleg ${n} von ${total}`,
    readAt: (time: string) => `${time} Uhr gelesen`,
    unclear: 'Eine Angabe ist nicht eindeutig',
    looksRight: 'Stimmt so',
    change: 'Ändern',
    accept: 'Übernehmen',
    discard: 'Verwerfen',
    isMissing: 'Diese Angabe fehlt im Beleg',
    rest: 'Alles Übrige wurde sicher erkannt',
    noMore: 'Weitere Angaben gibt es in dieser Vorlage nicht.',
    none: 'nichts gefunden',
    appliesHere:
      'Was Sie hier eintragen, gilt für diesen Beleg. Die Vorlage bleibt unverändert.',
    reason: {
      noValue:
        'An der markierten Stelle stand nichts Lesbares. Tragen Sie den Wert ein oder halten Sie fest, dass er im Beleg fehlt.',
      noEvidence:
        'Der Wert wurde gefunden, aber keine Stelle im Beleg dazu. Ohne Fundstelle lässt er sich nicht nachprüfen.',
      uncertain: 'Die Stelle im Beleg weicht von der gewohnten ab. Die Markierung sehen Sie links.',
      type: 'Der gefundene Wert passt nicht zu dem, was hier stehen sollte.',
      weak:
        'Die Schrift an dieser Stelle war schlecht lesbar. Bitte gleichen Sie den Wert mit dem Beleg ab.',
    },
  },

  templates: {
    title: 'Vorlagen',
    subtitle:
      'Eine Vorlage sagt dem Programm, wo in einem Beleg welche Angabe steht — und was damit geschehen soll.',
    newLabel: 'Neue Vorlage',
    search: 'Vorlage suchen',
    count: (n: number) => (n === 1 ? '1 Vorlage' : `${n} Vorlagen`),
    lastUsed: 'Zuletzt verwendet',
    all: 'Alle Vorlagen · A–Z',
    none: 'Noch keine Vorlage',
    noneDetail:
      'Öffnen Sie einen typischen Beleg, ziehen Sie Rahmen um die Stellen, die Sie brauchen — den Rest erledigt die Vorlage.',
    nothingFound: 'Keine Vorlage passt zu dieser Suche.',
    values: (n: number) => (n === 1 ? '1 Angabe' : `${n} Angaben`),
    changed: 'zuletzt geändert',
    readDocument: 'Beleg mit dieser Vorlage lesen',
    changeValues: 'Angaben ändern',
    delete: 'Vorlage löschen',
    deleteQuestion: (name: string) =>
      `Die Vorlage „${name}“ wird mit allen Angaben gelöscht. Das lässt sich nicht rückgängig machen.`,
    confirmDelete: 'Endgültig löschen',
    cancel: 'Abbrechen',
    reading: 'Beleg wird gelesen …',
  },

  assistant: {
    title: 'Neue Vorlage einrichten',
    editTitle: 'Vorlage ändern',
    backToTemplates: 'Vorlagen',
    steps: {
      document: 'Musterbeleg',
      values: 'Angaben markieren',
      result: 'Ergebnis',
      finish: 'Abschluss',
    },
    nextStep: 'Weiter',
    back: 'Zurück',

    document: {
      title: 'Ziehen Sie einen typischen Beleg hierher',
      subtitle:
        'Eine Rechnung, ein Lieferschein, eine Tabelle — irgendein Beispiel dieser Art. PDF, Foto, Scan oder Tabelle. Der Beleg bleibt auf diesem Gerät.',
      choose: 'Beleg auswählen',
      notice:
        'Sie richten das einmal ein. Jeden weiteren Beleg derselben Art lesen Sie danach mit einem Handgriff.',
      loaded: 'Dieser Beleg dient als Muster',
      other: 'Anderen Beleg wählen',
    },

    values: {
      title: 'Diese Angaben will ich haben',
      question: 'Was steht an dieser Stelle?',
      placeholder: 'z. B. Rechnungsnummer',
      accept: 'Übernehmen',
      cancel: 'Abbrechen',
      suggestions: ['Rechnungsnummer', 'Datum', 'Betrag', 'Absender', 'IBAN'],
      notice:
        'Ziehen Sie mit der Maus einen Rahmen um die Stelle im Beleg und sagen Sie, was dort steht. Mehr ist nicht nötig.',
      empty: 'Noch keine Angabe markiert.',
      marked: (n: number) =>
        n === 1 ? '1 Angabe markiert' : `${n} Angaben markiert`,
      notFound: 'an dieser Stelle steht nichts Lesbares',
      remove: 'Angabe entfernen',
      waiting: 'Ziehen Sie jetzt einen Rahmen im Beleg',
    },

    result: {
      title: 'Was soll aus jedem Beleg werden?',
      table: 'Eine Tabelle',
      tableDetail: 'Jeder Beleg wird eine Zeile. Zum Öffnen, Sortieren und Weitergeben.',
      file: 'Eine Datei je Beleg',
      fileDetail: 'Wenn ein anderes Programm die Daten einliest.',
      custom: 'Eigenes Format',
      customDetail: 'Nach Vorgabe Ihrer IT. Kommt in einer späteren Ausbaustufe.',
      preview: 'So sieht das Ergebnis aus',
      keyName: 'Namen im Ergebnis',
      keyDetail:
        'So heißen die Angaben in der Datei, die andere Programme einlesen. Der Vorschlag entsteht aus dem Klarnamen; ändern Sie ihn, wenn Ihre IT eine bestimmte Schreibweise verlangt.',
      keyError:
        'Erlaubt sind Buchstaben, Ziffern und Unterstriche; das erste Zeichen darf keine Ziffer sein.',
      duplicateKey: 'Diesen Namen trägt bereits eine andere Angabe.',
    },

    finish: {
      name: 'Name der Vorlage',
      namePlaceholder: 'z. B. Rechnung — Nordwind Maschinenbau',
      nameMissing: 'Geben Sie der Vorlage einen Namen.',
      summary: {
        template: 'Vorlage',
        values: 'Angaben',
        result: 'Ergebnis',
        unclear: 'Unklare Belege',
        unclearValue: 'kommen in die Prüfliste',
        unclearDetail: 'Der Rest läuft weiter durch.',
      },
      promise:
        'Beleg, Vorlage und Ergebnis bleiben auf diesem Gerät. Es besteht keine Verbindung nach außen.',
      save: 'Vorlage speichern',
      running: 'Wird gespeichert …',
    },
  },

  settings: {
    title: 'Einstellungen',
    subtitle: 'Wenig zu tun — das ist Absicht.',
    appearance: 'Erscheinungsbild',
    light: 'Hell',
    dark: 'Dunkel',
    lightDetail: 'Die Voreinstellung. Ruhiges Papiergrau.',
    darkDetail: 'Gleichwertig gepflegt, für dunkle Räume.',
    language: 'Sprache',
    german: 'Deutsch',
    germanCode: 'DE',
    germanDetail: 'Die Voreinstellung.',
    english: 'Englisch',
    englishCode: 'EN',
    englishDetail: 'Die englische Oberfläche.',
    privacy: 'Datenschutz und Technik',
    noConnection: 'Es besteht keine Verbindung nach außen',
    noConnectionDetail:
      'Belege, Vorlagen und Ergebnisse verlassen dieses Gerät nicht. Es gibt keinen Netzwerkzugang, der sich einschalten ließe.',
    technical: 'Technische Details',
    technicalDetail:
      'Ab hier stehen die Begriffe des Maschinenraums. Sie sind für die IT gedacht, nicht für den Arbeitsalltag.',
    textRecognition: 'Texterkennung',
    localEngine: 'lokal · Tesseract',
    storageLocation: 'Speicherort',
    thisDevice: 'dieses Gerät',
  },

  document: {
    state: {
      filed: 'abgelegt',
      read: 'gelesen',
      waiting: 'wartet auf Prüfung',
    },
    saveResult: 'Ergebnis sichern',
    loading: 'Beleg wird gelesen …',
    formats: 'PDF, Tabellen und Bilder',
  },

  viewer: {
    page: 'Seite',
    of: 'von',
    previous: 'Vorherige Seite',
    next: 'Nächste Seite',
    zoomOut: 'Verkleinern',
    zoomIn: 'Vergrößern',
    resetZoom: 'Ansicht zurücksetzen',
    rotate: 'Seite drehen',
    sheet: 'Blatt',
  },

  highlight: {
    newLabel: 'Rahmen aufziehen',
    delete: 'Markierung entfernen',
    none: 'Noch nichts markiert',
    count: (n: number) => (n === 1 ? '1 Markierung' : `${n} Markierungen`),
  },

  info: {
    pages: 'Seiten',
    mode: 'Betriebsart',
    sidecar: 'Backend',
  },

  mode: {
    airgap: 'Air-Gap — keine ausgehenden Verbindungen',
    onprem: 'On-Premise',
    cloud: 'Cloud freigeschaltet',
  },

  errors: {
    title: 'Es ist ein Fehler aufgetreten',
    showDetails: 'Technische Details',
    close: 'Hinweis schließen',
    messages: {
      'file-not-found':
        'Der Beleg wurde nicht gefunden. Möglicherweise wurde er verschoben oder gelöscht.',
      'format-not-supported':
        'Dieses Format lässt sich nicht lesen. Möglich sind PDF, Tabellen (xlsx, xls, csv) und Bilder (png, jpg, tiff).',
      'file-too-large':
        'Der Beleg ist zu groß. Sehr große Scans lassen sich oft seitenweise aufteilen.',
      'document-corrupt':
        'Der Beleg ist beschädigt oder unlesbar. Er lässt sich mit einem anderen Programm möglicherweise reparieren.',
      'document-password-protected':
        'Der Beleg ist mit einem Kennwort geschützt. Bitte entfernen Sie den Schutz und öffnen Sie ihn erneut.',
      'document-empty': 'Der Beleg enthält nichts, was sich auswerten ließe.',
      'unknown-document': 'Der Beleg ist nicht mehr geöffnet. Bitte wählen Sie ihn erneut.',
      'page-not-found': 'Diese Seite gibt es im Beleg nicht.',
      'path-not-allowed':
        'Der Beleg liegt außerhalb der für diese Sitzung freigegebenen Ordner.',
      'not-authorized': 'Die Sitzung ist abgelaufen. Bitte starten Sie die Anwendung neu.',
      'egress-denied':
        'Es sind keine ausgehenden Verbindungen erlaubt. Das ist so vorgesehen — alle Belege bleiben auf diesem Gerät.',
      'document-kind-invalid':
        'Die Beschreibung einer Belegart ist fehlerhaft. Einzelheiten stehen im lokalen Protokoll.',
      'document-kind-unknown': 'Diese Belegart ist auf diesem Gerät nicht beschrieben.',
      'sidecar-not-connected': 'Substrakt läuft nicht. Bitte starten Sie die Anwendung neu.',
      'sidecar-unreachable': 'Substrakt antwortet nicht. Bitte starten Sie die Anwendung neu.',
      'response-unreadable': 'Die Antwort war unlesbar.',
      'unknown-error': 'Ein unerwarteter Fehler ist aufgetreten.',
      'internal-error':
        'Ein unerwarteter Fehler ist aufgetreten. Einzelheiten stehen im lokalen Protokoll.',
      'unexpected-error':
        'Ein unerwarteter Fehler ist aufgetreten. Einzelheiten stehen im lokalen Protokoll.',
    } as Record<string, string>,
  },
}
