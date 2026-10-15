/**
 * English interface copy and the vocabulary that keeps it consistent.
 *
 * | German screen word | English screen word |
 * |---|---|
 * | Übersicht, Prüfen, Vorlagen, Einstellungen | Overview, Review, Templates, Settings |
 * | Beleg | document |
 * | Vorlage | template |
 * | Angabe | detail |
 * | sicher erkannt | recognised |
 * | nicht eindeutig | unclear |
 * | wartet auf Prüfung | waiting for review |
 * | abgelegt | filed |
 * | Alle Belege bleiben auf diesem Gerät. | All documents stay on this device. |
 *
 * Engine-room terms remain under “Settings → Technical details”. The other
 * screens use the short words a clerk needs to finish the work.
 */

import type { Texts } from './index'

export const en: Texts = {
  app: {
    title: 'Substrakt',
    version: 'Version',
    promise: 'All documents stay on this device.',
  },

  places: {
    overview: 'Overview',
    review: 'Review',
    templates: 'Templates',
    settings: 'Settings',
  },

  theme: {
    toggle: 'Light or dark',
  },

  keys: {
    enter: 'Enter',
  },

  time: {
    justNow: 'just now',
    minuteAgo: '1 minute ago',
    minutesAgo: (minutes: number) => `${minutes} minutes ago`,
    hourAgo: '1 hour ago',
    hoursAgo: (hours: number) => `${hours} hours ago`,
    yesterday: 'yesterday',
    daysAgo: (days: number) => `${days} days ago`,
  },

  state: {
    running: 'Everything is running',
    starting: 'Substrakt is starting',
    startingDetail: 'One moment — the reader is getting ready.',
    unavailable: 'Substrakt is not running',
    unavailableDetail: 'Please restart the application.',
    ready: (templates: number) =>
      templates === 1 ? '1 template set up' : `${templates} templates set up`,
    noTemplates: 'No template set up yet',
  },

  overview: {
    title: 'Overview',
    subtitle: 'What has been read appears here. You only need to act when a detail is unclear.',
    documents: 'Documents in this session',
    waiting: 'waiting for your review',
    gaps: 'with a missing detail',
    reviewNow: 'Review now',
    recent: 'Recently processed',
    lastRead: 'last read',
    nothingYet: 'No document has been read in this session yet.',
    nothingYetDetail:
      'Set up a template, then use it to read every other document of the same kind.',
    firstTemplate: 'Set up the first template',
    readDocument: 'Read document',
    folders: 'Watched folders',
    folderDetail:
      'Folders are not watched yet. Until then, choose each document yourself — the template works in the same way.',
  },

  review: {
    empty: 'Nothing to review',
    emptyDetail: 'All details were recognised clearly.',
    documentOf: (n: number, total: number) => `Document ${n} of ${total}`,
    readAt: (time: string) => `read at ${time}`,
    unclear: 'One detail is unclear',
    looksRight: 'Looks right',
    change: 'Change',
    accept: 'Accept',
    discard: 'Discard',
    isMissing: 'This detail is missing from the document',
    rest: 'Everything else was recognised',
    noMore: 'There are no other details in this template.',
    none: 'nothing found',
    appliesHere:
      'What you enter here applies to this document. The template stays unchanged.',
    reason: {
      noValue:
        'There was nothing readable in the marked area. Enter the value or mark it as missing from the document.',
      noEvidence:
        'The value was found, but its place in the document was not. It cannot be checked without that place.',
      uncertain: 'The place differs from the usual one. The mark is shown on the left.',
      type: 'The value does not match what should be here.',
      weak: 'The text here was hard to read. Please compare the value with the document.',
    },
  },

  templates: {
    title: 'Templates',
    subtitle:
      'A template tells the application where each detail is in a document and what to do with it.',
    newLabel: 'New template',
    search: 'Search templates',
    count: (n: number) => (n === 1 ? '1 template' : `${n} templates`),
    lastUsed: 'Last used',
    all: 'All templates · A–Z',
    none: 'No template yet',
    noneDetail:
      'Open a typical document and draw boxes around the details you need. The template does the rest.',
    nothingFound: 'No template matches this search.',
    values: (n: number) => (n === 1 ? '1 detail' : `${n} details`),
    changed: 'last changed',
    readDocument: 'Read a document with this template',
    changeValues: 'Change details',
    delete: 'Delete template',
    deleteQuestion: (name: string) =>
      `The template “${name}” and all its details will be deleted. This cannot be undone.`,
    confirmDelete: 'Delete permanently',
    cancel: 'Cancel',
    reading: 'Reading document …',
  },

  assistant: {
    title: 'Set up a new template',
    editTitle: 'Change template',
    backToTemplates: 'Templates',
    steps: {
      document: 'Sample document',
      values: 'Mark details',
      result: 'Result',
      finish: 'Finish',
    },
    nextStep: 'Next',
    back: 'Back',

    document: {
      title: 'Drop a typical document here',
      subtitle:
        'Use an invoice, delivery note or spreadsheet of this kind. PDF, photo, scan and spreadsheet files work. The document stays on this device.',
      choose: 'Choose document',
      notice:
        'Set this up once. After that, you can read every document of the same kind in one step.',
      loaded: 'This document is the sample',
      other: 'Choose another document',
    },

    values: {
      title: 'These are the details I need',
      question: 'What is shown here?',
      placeholder: 'For example, invoice number',
      accept: 'Accept',
      cancel: 'Cancel',
      suggestions: ['Invoice number', 'Date', 'Amount', 'Sender', 'IBAN'],
      notice:
        'Draw a box around a place in the document and say what it contains. That is all you need to do.',
      empty: 'No detail marked yet.',
      marked: (n: number) => (n === 1 ? '1 detail marked' : `${n} details marked`),
      notFound: 'there is nothing readable here',
      remove: 'Remove detail',
      waiting: 'Draw a box in the document now',
    },

    result: {
      title: 'What should each document become?',
      table: 'One table',
      tableDetail: 'Each document becomes one row. Easy to open, sort and share.',
      file: 'One file per document',
      fileDetail: 'Use this when another application reads the data.',
      custom: 'Custom format',
      customDetail: 'Defined by your IT team. This will come in a later stage.',
      preview: 'This is what the result looks like',
      keyName: 'Names in the result',
      keyDetail:
        'These names identify the details in files read by other applications. The suggestion comes from the display name. Change it if your IT team requires another spelling.',
      keyError:
        'Use letters, numbers and underscores. The first character cannot be a number.',
      duplicateKey: 'Another detail already uses this name.',
    },

    finish: {
      name: 'Template name',
      namePlaceholder: 'For example, Invoice — Northwind Engineering',
      nameMissing: 'Give the template a name.',
      summary: {
        template: 'Template',
        values: 'Details',
        result: 'Result',
        unclear: 'Unclear documents',
        unclearValue: 'go to the review list',
        unclearDetail: 'Everything else continues.',
      },
      promise:
        'The document, template and result stay on this device. There is no outside connection.',
      save: 'Save template',
      running: 'Saving …',
    },
  },

  settings: {
    title: 'Settings',
    subtitle: 'There is little to do here — by design.',
    appearance: 'Appearance',
    light: 'Light',
    dark: 'Dark',
    lightDetail: 'The default. A calm paper grey.',
    darkDetail: 'Equally complete, for dark rooms.',
    language: 'Language',
    german: 'German',
    germanCode: 'DE',
    germanDetail: 'The default.',
    english: 'English',
    englishCode: 'EN',
    englishDetail: 'The English interface.',
    privacy: 'Privacy and technology',
    noConnection: 'There is no outside connection',
    noConnectionDetail:
      'Documents, templates and results never leave this device. There is no network access to turn on.',
    technical: 'Technical details',
    technicalDetail:
      'The terms below describe the engine room. They are for IT staff, not everyday work.',
    textRecognition: 'Text recognition',
    localEngine: 'local · Tesseract',
    storageLocation: 'Storage location',
    thisDevice: 'this device',
  },

  document: {
    state: {
      filed: 'filed',
      read: 'read',
      waiting: 'waiting for review',
    },
    saveResult: 'Save result',
    loading: 'Reading document …',
    formats: 'PDF, spreadsheets and images',
  },

  viewer: {
    page: 'Page',
    of: 'of',
    previous: 'Previous page',
    next: 'Next page',
    zoomOut: 'Zoom out',
    zoomIn: 'Zoom in',
    resetZoom: 'Reset view',
    rotate: 'Rotate page',
    sheet: 'Sheet',
  },

  highlight: {
    newLabel: 'Draw box',
    delete: 'Remove mark',
    none: 'Nothing marked yet',
    count: (n: number) => (n === 1 ? '1 mark' : `${n} marks`),
  },

  info: {
    pages: 'Pages',
    mode: 'Mode',
    sidecar: 'Backend',
  },

  mode: {
    airgap: 'Air-gap — no outgoing connections',
    onprem: 'On-premise',
    cloud: 'Cloud enabled',
  },

  errors: {
    title: 'Something went wrong',
    showDetails: 'Technical details',
    close: 'Close message',
    messages: {
      'file-not-found': 'The document was not found. It may have been moved or deleted.',
      'format-not-supported':
        'This format cannot be read. You can use PDF, spreadsheets (xlsx, xls, csv) and images (png, jpg, tiff).',
      'file-too-large': 'The document is too large. Splitting a large scan into pages may help.',
      'document-corrupt':
        'The document is damaged or unreadable. Another application may be able to repair it.',
      'document-password-protected':
        'The document is password protected. Remove the protection and open it again.',
      'document-empty': 'The document contains nothing that can be read.',
      'unknown-document': 'The document is no longer open. Please choose it again.',
      'page-not-found': 'This page is not in the document.',
      'path-not-allowed': 'The document is outside the folders allowed for this session.',
      'not-authorized': 'The session has expired. Please restart the application.',
      'egress-denied':
        'Outgoing connections are not allowed. This is intentional — all documents stay on this device.',
      'document-kind-invalid':
        'A document description is invalid. Details are in the local log.',
      'document-kind-unknown': 'This kind of document is not described on this device.',
      'sidecar-not-connected': 'Substrakt is not running. Please restart the application.',
      'sidecar-unreachable': 'Substrakt is not responding. Please restart the application.',
      'response-unreadable': 'The response could not be read.',
      'unknown-error': 'An unexpected error occurred.',
      'internal-error': 'An unexpected error occurred. Details are in the local log.',
      'unexpected-error': 'An unexpected error occurred. Details are in the local log.',
    },
  },
}
