// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Accent _$AccentFromJson(Map<String, dynamic> json) => Accent(
  form: json['form'] as String,
  exact: json['exact'] as bool,
  ambiguous: json['ambiguous'] as bool? ?? false,
  clitic: json['clitic'] as bool? ?? false,
);

const _$AccentFieldMap = <String, String>{
  'form': 'form',
  'exact': 'exact',
  'ambiguous': 'ambiguous',
  'clitic': 'clitic',
};

Map<String, dynamic> _$AccentToJson(Accent instance) => <String, dynamic>{
  'form': instance.form,
  'exact': instance.exact,
  'ambiguous': instance.ambiguous,
  'clitic': instance.clitic,
};

ProblemMessage _$ProblemMessageFromJson(Map<String, dynamic> json) =>
    ProblemMessage(
      key: json['key'] as String,
      params: (json['params'] as Map<String, dynamic>).map(
        (k, e) => MapEntry(k, e as Object),
      ),
    );

const _$ProblemMessageFieldMap = <String, String>{
  'key': 'key',
  'params': 'params',
};

Map<String, dynamic> _$ProblemMessageToJson(ProblemMessage instance) =>
    <String, dynamic>{'key': instance.key, 'params': instance.params};

Word _$WordFromJson(Map<String, dynamic> json) => Word(
  id: (json['id'] as num).toInt(),
  text: json['text'] as String,
  lemma: json['lemma'] as String,
  upos: json['upos'] as String,
  xpos: json['xpos'] as String,
  feats: Map<String, String>.from(json['feats'] as Map),
  head: (json['head'] as num?)?.toInt() ?? 0,
  deprel: json['deprel'] as String? ?? '',
  startChar: (json['start_char'] as num).toInt(),
  endChar: (json['end_char'] as num).toInt(),
  problems:
      (json['problems'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      const [],
  problemMessages:
      (json['problem_messages'] as List<dynamic>?)
          ?.map(
            (e) => e == null
                ? null
                : ProblemMessage.fromJson(e as Map<String, dynamic>),
          )
          .toList() ??
      const [],
  accent: json['accent'] == null
      ? null
      : Accent.fromJson(json['accent'] as Map<String, dynamic>),
  reading: json['reading'] as String? ?? '',
  seen: (json['seen'] as num?)?.toInt(),
);

const _$WordFieldMap = <String, String>{
  'id': 'id',
  'text': 'text',
  'lemma': 'lemma',
  'upos': 'upos',
  'xpos': 'xpos',
  'feats': 'feats',
  'head': 'head',
  'deprel': 'deprel',
  'startChar': 'start_char',
  'endChar': 'end_char',
  'problems': 'problems',
  'problemMessages': 'problem_messages',
  'accent': 'accent',
  'reading': 'reading',
  'seen': 'seen',
};

Map<String, dynamic> _$WordToJson(Word instance) => <String, dynamic>{
  'id': instance.id,
  'text': instance.text,
  'lemma': instance.lemma,
  'upos': instance.upos,
  'xpos': instance.xpos,
  'feats': instance.feats,
  'head': instance.head,
  'deprel': instance.deprel,
  'start_char': instance.startChar,
  'end_char': instance.endChar,
  'problems': instance.problems,
  'problem_messages': instance.problemMessages.map((e) => e?.toJson()).toList(),
  'accent': instance.accent?.toJson(),
  'reading': instance.reading,
  'seen': instance.seen,
};

Sentence _$SentenceFromJson(Map<String, dynamic> json) => Sentence(
  text: json['text'] as String,
  words: (json['words'] as List<dynamic>)
      .map((e) => Word.fromJson(e as Map<String, dynamic>))
      .toList(),
);

const _$SentenceFieldMap = <String, String>{'text': 'text', 'words': 'words'};

Map<String, dynamic> _$SentenceToJson(Sentence instance) => <String, dynamic>{
  'text': instance.text,
  'words': instance.words.map((e) => e.toJson()).toList(),
};

Translation _$TranslationFromJson(Map<String, dynamic> json) => Translation(
  links:
      (json['links'] as List<dynamic>?)
          ?.map((e) => Link.fromJson(e as List<dynamic>))
          .toList() ??
      const [],
  guesses:
      (json['guesses'] as List<dynamic>?)
          ?.map((e) => Link.fromJson(e as List<dynamic>))
          .toList() ??
      const [],
  text: json['text'] as String? ?? '',
  sentences:
      (json['sentences'] as List<dynamic>?)
          ?.map((e) => Sentence.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  error: json['error'] as String? ?? '',
  errorCode: json['error_code'] as String? ?? '',
  errorParams:
      (json['error_params'] as Map<String, dynamic>?)?.map(
        (k, e) => MapEntry(k, e as Object),
      ) ??
      const {},
);

const _$TranslationFieldMap = <String, String>{
  'links': 'links',
  'guesses': 'guesses',
  'text': 'text',
  'sentences': 'sentences',
  'error': 'error',
  'errorCode': 'error_code',
  'errorParams': 'error_params',
};

Map<String, dynamic> _$TranslationToJson(Translation instance) =>
    <String, dynamic>{
      'links': instance.links.map((e) => e.toJson()).toList(),
      'guesses': instance.guesses.map((e) => e.toJson()).toList(),
      'text': instance.text,
      'sentences': instance.sentences.map((e) => e.toJson()).toList(),
      'error': instance.error,
      'error_code': instance.errorCode,
      'error_params': instance.errorParams,
    };

ClassifyResponse _$ClassifyResponseFromJson(Map<String, dynamic> json) =>
    ClassifyResponse(
      type: json['type'] as String,
      language: json['language'] as String,
      source: $enumDecode(_$SourceEnumMap, json['source']),
      text: json['text'] as String,
      sentences: (json['sentences'] as List<dynamic>)
          .map((e) => Sentence.fromJson(e as Map<String, dynamic>))
          .toList(),
      translation: json['translation'] == null
          ? null
          : Translation.fromJson(json['translation'] as Map<String, dynamic>),
    );

const _$ClassifyResponseFieldMap = <String, String>{
  'type': 'type',
  'language': 'language',
  'source': 'source',
  'text': 'text',
  'sentences': 'sentences',
  'translation': 'translation',
};

Map<String, dynamic> _$ClassifyResponseToJson(ClassifyResponse instance) =>
    <String, dynamic>{
      'type': instance.type,
      'language': instance.language,
      'source': _$SourceEnumMap[instance.source]!,
      'text': instance.text,
      'sentences': instance.sentences.map((e) => e.toJson()).toList(),
      'translation': instance.translation?.toJson(),
    };

const _$SourceEnumMap = {Source.study: 'study', Source.en: 'en'};

LanguageInfo _$LanguageInfoFromJson(Map<String, dynamic> json) => LanguageInfo(
  code: json['code'] as String,
  name: json['name'] as String,
  tagName: json['tag_name'] as String,
  placeholder: json['placeholder'] as String,
  variants: (json['variants'] as List<dynamic>)
      .map((e) => e as String)
      .toList(),
  lightNote: json['light_note'] as String,
  hasAccents: json['has_accents'] as bool,
  direction: $enumDecode(_$ScriptDirectionEnumMap, json['direction']),
  speech: json['speech'] as String,
  dictionaryLinks: (json['dictionary_links'] as List<dynamic>)
      .map((e) => DictionaryLink.fromJson(e as List<dynamic>))
      .toList(),
  uiLocale: json['ui_locale'] as String? ?? '',
  nativeName: json['native_name'] as String? ?? '',
);

const _$LanguageInfoFieldMap = <String, String>{
  'code': 'code',
  'name': 'name',
  'tagName': 'tag_name',
  'placeholder': 'placeholder',
  'variants': 'variants',
  'lightNote': 'light_note',
  'hasAccents': 'has_accents',
  'direction': 'direction',
  'speech': 'speech',
  'dictionaryLinks': 'dictionary_links',
  'uiLocale': 'ui_locale',
  'nativeName': 'native_name',
};

Map<String, dynamic> _$LanguageInfoToJson(
  LanguageInfo instance,
) => <String, dynamic>{
  'code': instance.code,
  'name': instance.name,
  'tag_name': instance.tagName,
  'placeholder': instance.placeholder,
  'variants': instance.variants,
  'light_note': instance.lightNote,
  'has_accents': instance.hasAccents,
  'direction': _$ScriptDirectionEnumMap[instance.direction]!,
  'speech': instance.speech,
  'dictionary_links': instance.dictionaryLinks.map((e) => e.toJson()).toList(),
  'ui_locale': instance.uiLocale,
  'native_name': instance.nativeName,
};

const _$ScriptDirectionEnumMap = {
  ScriptDirection.ltr: 'ltr',
  ScriptDirection.rtl: 'rtl',
};

Locale _$LocaleFromJson(Map<String, dynamic> json) => Locale(
  code: json['code'] as String,
  name: json['name'] as String,
  direction: $enumDecode(_$ScriptDirectionEnumMap, json['direction']),
);

const _$LocaleFieldMap = <String, String>{
  'code': 'code',
  'name': 'name',
  'direction': 'direction',
};

Map<String, dynamic> _$LocaleToJson(Locale instance) => <String, dynamic>{
  'code': instance.code,
  'name': instance.name,
  'direction': _$ScriptDirectionEnumMap[instance.direction]!,
};

LocalesResponse _$LocalesResponseFromJson(Map<String, dynamic> json) =>
    LocalesResponse(
      defaultCode: json['default'] as String,
      locales: (json['locales'] as List<dynamic>)
          .map((e) => Locale.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

const _$LocalesResponseFieldMap = <String, String>{
  'defaultCode': 'default',
  'locales': 'locales',
};

Map<String, dynamic> _$LocalesResponseToJson(LocalesResponse instance) =>
    <String, dynamic>{
      'default': instance.defaultCode,
      'locales': instance.locales.map((e) => e.toJson()).toList(),
    };

LanguagesResponse _$LanguagesResponseFromJson(Map<String, dynamic> json) =>
    LanguagesResponse(
      languages: (json['languages'] as List<dynamic>)
          .map((e) => LanguageInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      english: LanguageInfo.fromJson(json['english'] as Map<String, dynamic>),
      largeByDefault: json['large_by_default'] as bool,
    );

const _$LanguagesResponseFieldMap = <String, String>{
  'languages': 'languages',
  'english': 'english',
  'largeByDefault': 'large_by_default',
};

Map<String, dynamic> _$LanguagesResponseToJson(LanguagesResponse instance) =>
    <String, dynamic>{
      'languages': instance.languages.map((e) => e.toJson()).toList(),
      'english': instance.english.toJson(),
      'large_by_default': instance.largeByDefault,
    };

LoadingModel _$LoadingModelFromJson(Map<String, dynamic> json) => LoadingModel(
  language: json['language'] as String,
  variant: json['variant'] as String,
);

const _$LoadingModelFieldMap = <String, String>{
  'language': 'language',
  'variant': 'variant',
};

Map<String, dynamic> _$LoadingModelToJson(LoadingModel instance) =>
    <String, dynamic>{
      'language': instance.language,
      'variant': instance.variant,
    };

StatusResponse _$StatusResponseFromJson(
  Map<String, dynamic> json,
) => StatusResponse(
  loading: json['loading'] as String?,
  loadingModel: json['loading_model'] == null
      ? null
      : LoadingModel.fromJson(json['loading_model'] as Map<String, dynamic>),
  loaded: (json['loaded'] as List<dynamic>).map((e) => e as String).toList(),
);

const _$StatusResponseFieldMap = <String, String>{
  'loading': 'loading',
  'loadingModel': 'loading_model',
  'loaded': 'loaded',
};

Map<String, dynamic> _$StatusResponseToJson(StatusResponse instance) =>
    <String, dynamic>{
      'loading': instance.loading,
      'loading_model': instance.loadingModel?.toJson(),
      'loaded': instance.loaded,
    };

Counts _$CountsFromJson(Map<String, dynamic> json) => Counts(
  total: (json['total'] as num).toInt(),
  newCards: (json['new'] as num).toInt(),
  learning: (json['learning'] as num).toInt(),
  due: (json['due'] as num).toInt(),
);

const _$CountsFieldMap = <String, String>{
  'total': 'total',
  'newCards': 'new',
  'learning': 'learning',
  'due': 'due',
};

Map<String, dynamic> _$CountsToJson(Counts instance) => <String, dynamic>{
  'total': instance.total,
  'new': instance.newCards,
  'learning': instance.learning,
  'due': instance.due,
};

Deck _$DeckFromJson(Map<String, dynamic> json) => Deck(
  id: (json['id'] as num).toInt(),
  name: json['name'] as String,
  language: json['language'] as String,
  path: (json['path'] as List<dynamic>).map((e) => e as String).toList(),
  counts: Counts.fromJson(json['counts'] as Map<String, dynamic>),
);

const _$DeckFieldMap = <String, String>{
  'id': 'id',
  'name': 'name',
  'language': 'language',
  'path': 'path',
  'counts': 'counts',
};

Map<String, dynamic> _$DeckToJson(Deck instance) => <String, dynamic>{
  'id': instance.id,
  'name': instance.name,
  'language': instance.language,
  'path': instance.path,
  'counts': instance.counts.toJson(),
};

DecksResponse _$DecksResponseFromJson(Map<String, dynamic> json) =>
    DecksResponse(
      decks: (json['decks'] as List<dynamic>)
          .map((e) => Deck.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

const _$DecksResponseFieldMap = <String, String>{'decks': 'decks'};

Map<String, dynamic> _$DecksResponseToJson(DecksResponse instance) =>
    <String, dynamic>{'decks': instance.decks.map((e) => e.toJson()).toList()};

Media _$MediaFromJson(Map<String, dynamic> json) => Media(
  kind: $enumDecode(_$MediaKindEnumMap, json['kind']),
  url: json['url'] as String,
);

const _$MediaFieldMap = <String, String>{'kind': 'kind', 'url': 'url'};

Map<String, dynamic> _$MediaToJson(Media instance) => <String, dynamic>{
  'kind': _$MediaKindEnumMap[instance.kind]!,
  'url': instance.url,
};

const _$MediaKindEnumMap = {MediaKind.image: 'image', MediaKind.audio: 'audio'};

NextCard _$NextCardFromJson(Map<String, dynamic> json) => NextCard(
  cardId: (json['card_id'] as num).toInt(),
  direction: $enumDecode(_$CardDirectionEnumMap, json['direction']),
  language: json['language'] as String,
  prompt: json['prompt'] as String,
  media: (json['media'] as List<dynamic>)
      .map((e) => Media.fromJson(e as Map<String, dynamic>))
      .toList(),
  promptSentences: (json['prompt_sentences'] as List<dynamic>)
      .map((e) => Sentence.fromJson(e as Map<String, dynamic>))
      .toList(),
  counts: Counts.fromJson(json['counts'] as Map<String, dynamic>),
);

const _$NextCardFieldMap = <String, String>{
  'cardId': 'card_id',
  'direction': 'direction',
  'language': 'language',
  'prompt': 'prompt',
  'media': 'media',
  'promptSentences': 'prompt_sentences',
  'counts': 'counts',
};

Map<String, dynamic> _$NextCardToJson(NextCard instance) => <String, dynamic>{
  'card_id': instance.cardId,
  'direction': _$CardDirectionEnumMap[instance.direction]!,
  'language': instance.language,
  'prompt': instance.prompt,
  'media': instance.media.map((e) => e.toJson()).toList(),
  'prompt_sentences': instance.promptSentences.map((e) => e.toJson()).toList(),
  'counts': instance.counts.toJson(),
};

const _$CardDirectionEnumMap = {
  CardDirection.toStudy: 'to_study',
  CardDirection.toEnglish: 'to_english',
  CardDirection.listen: 'listen',
  CardDirection.dictation: 'dictation',
};

NoCard _$NoCardFromJson(Map<String, dynamic> json) => NoCard(
  done: json['done'] as bool? ?? true,
  nextDue: json['next_due'] as String?,
  counts: Counts.fromJson(json['counts'] as Map<String, dynamic>),
);

const _$NoCardFieldMap = <String, String>{
  'done': 'done',
  'nextDue': 'next_due',
  'counts': 'counts',
};

Map<String, dynamic> _$NoCardToJson(NoCard instance) => <String, dynamic>{
  'done': instance.done,
  'next_due': instance.nextDue,
  'counts': instance.counts.toJson(),
};

LinkedAnswer _$LinkedAnswerFromJson(Map<String, dynamic> json) => LinkedAnswer(
  links:
      (json['links'] as List<dynamic>?)
          ?.map((e) => Link.fromJson(e as List<dynamic>))
          .toList() ??
      const [],
  guesses:
      (json['guesses'] as List<dynamic>?)
          ?.map((e) => Link.fromJson(e as List<dynamic>))
          .toList() ??
      const [],
  sentences: (json['sentences'] as List<dynamic>)
      .map((e) => Sentence.fromJson(e as Map<String, dynamic>))
      .toList(),
);

const _$LinkedAnswerFieldMap = <String, String>{
  'links': 'links',
  'guesses': 'guesses',
  'sentences': 'sentences',
};

Map<String, dynamic> _$LinkedAnswerToJson(LinkedAnswer instance) =>
    <String, dynamic>{
      'links': instance.links.map((e) => e.toJson()).toList(),
      'guesses': instance.guesses.map((e) => e.toJson()).toList(),
      'sentences': instance.sentences.map((e) => e.toJson()).toList(),
    };

AnswerResponse _$AnswerResponseFromJson(Map<String, dynamic> json) =>
    AnswerResponse(
      reviewId: (json['review_id'] as num).toInt(),
      rating: (json['rating'] as num).toInt(),
      nextDue: json['next_due'] as String,
      diff: (json['diff'] as List<dynamic>)
          .map((e) => DiffSpan.fromJson(e as List<dynamic>))
          .toList(),
      answers: (json['answers'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      media: (json['media'] as List<dynamic>)
          .map((e) => Media.fromJson(e as Map<String, dynamic>))
          .toList(),
      prompt: json['prompt'] as String,
      promptSentences: (json['prompt_sentences'] as List<dynamic>)
          .map((e) => Sentence.fromJson(e as Map<String, dynamic>))
          .toList(),
      typed: LinkedAnswer.fromJson(json['typed'] as Map<String, dynamic>),
      correct: LinkedAnswer.fromJson(json['correct'] as Map<String, dynamic>),
    );

const _$AnswerResponseFieldMap = <String, String>{
  'reviewId': 'review_id',
  'rating': 'rating',
  'nextDue': 'next_due',
  'diff': 'diff',
  'answers': 'answers',
  'media': 'media',
  'prompt': 'prompt',
  'promptSentences': 'prompt_sentences',
  'typed': 'typed',
  'correct': 'correct',
};

Map<String, dynamic> _$AnswerResponseToJson(
  AnswerResponse instance,
) => <String, dynamic>{
  'review_id': instance.reviewId,
  'rating': instance.rating,
  'next_due': instance.nextDue,
  'diff': instance.diff.map((e) => e.toJson()).toList(),
  'answers': instance.answers,
  'media': instance.media.map((e) => e.toJson()).toList(),
  'prompt': instance.prompt,
  'prompt_sentences': instance.promptSentences.map((e) => e.toJson()).toList(),
  'typed': instance.typed.toJson(),
  'correct': instance.correct.toJson(),
};

RatingResponse _$RatingResponseFromJson(Map<String, dynamic> json) =>
    RatingResponse(
      rating: (json['rating'] as num).toInt(),
      nextDue: json['next_due'] as String,
    );

const _$RatingResponseFieldMap = <String, String>{
  'rating': 'rating',
  'nextDue': 'next_due',
};

Map<String, dynamic> _$RatingResponseToJson(RatingResponse instance) =>
    <String, dynamic>{'rating': instance.rating, 'next_due': instance.nextDue};

FlashcardUser _$FlashcardUserFromJson(Map<String, dynamic> json) =>
    FlashcardUser(id: json['id'] as String, name: json['name'] as String);

const _$FlashcardUserFieldMap = <String, String>{'id': 'id', 'name': 'name'};

Map<String, dynamic> _$FlashcardUserToJson(FlashcardUser instance) =>
    <String, dynamic>{'id': instance.id, 'name': instance.name};

UsersResponse _$UsersResponseFromJson(Map<String, dynamic> json) =>
    UsersResponse(
      me: json['me'] as String,
      admin: json['admin'] as bool,
      users: (json['users'] as List<dynamic>)
          .map((e) => FlashcardUser.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

const _$UsersResponseFieldMap = <String, String>{
  'me': 'me',
  'admin': 'admin',
  'users': 'users',
};

Map<String, dynamic> _$UsersResponseToJson(UsersResponse instance) =>
    <String, dynamic>{
      'me': instance.me,
      'admin': instance.admin,
      'users': instance.users.map((e) => e.toJson()).toList(),
    };

StatsDay _$StatsDayFromJson(Map<String, dynamic> json) => StatsDay(
  date: json['date'] as String,
  reviews: (json['reviews'] as num).toInt(),
  passed: (json['passed'] as num).toInt(),
);

const _$StatsDayFieldMap = <String, String>{
  'date': 'date',
  'reviews': 'reviews',
  'passed': 'passed',
};

Map<String, dynamic> _$StatsDayToJson(StatsDay instance) => <String, dynamic>{
  'date': instance.date,
  'reviews': instance.reviews,
  'passed': instance.passed,
};

StatsResponse _$StatsResponseFromJson(Map<String, dynamic> json) =>
    StatsResponse(
      counts: json['counts'] == null
          ? null
          : _countsOrNull(json['counts'] as Map<String, dynamic>),
      reviews: (json['reviews'] as num).toInt(),
      successRate: (json['success_rate'] as num?)?.toDouble(),
      lapses: (json['lapses'] as num).toInt(),
      streakDays: (json['streak_days'] as num).toInt(),
      days: (json['days'] as List<dynamic>)
          .map((e) => StatsDay.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

const _$StatsResponseFieldMap = <String, String>{
  'counts': 'counts',
  'reviews': 'reviews',
  'successRate': 'success_rate',
  'lapses': 'lapses',
  'streakDays': 'streak_days',
  'days': 'days',
};

Map<String, dynamic> _$StatsResponseToJson(StatsResponse instance) =>
    <String, dynamic>{
      'counts': _countsOrEmpty(instance.counts),
      'reviews': instance.reviews,
      'success_rate': instance.successRate,
      'lapses': instance.lapses,
      'streak_days': instance.streakDays,
      'days': instance.days.map((e) => e.toJson()).toList(),
    };

ExplainQuestion _$ExplainQuestionFromJson(Map<String, dynamic> json) =>
    ExplainQuestion(
      id: json['id'] as String,
      label: json['label'] as String,
      where: $enumDecode(_$QuestionPlaceEnumMap, json['where']),
    );

const _$ExplainQuestionFieldMap = <String, String>{
  'id': 'id',
  'label': 'label',
  'where': 'where',
};

Map<String, dynamic> _$ExplainQuestionToJson(ExplainQuestion instance) =>
    <String, dynamic>{
      'id': instance.id,
      'label': instance.label,
      'where': _$QuestionPlaceEnumMap[instance.where]!,
    };

const _$QuestionPlaceEnumMap = {
  QuestionPlace.sentence: 'sentence',
  QuestionPlace.card: 'card',
};

QuestionsResponse _$QuestionsResponseFromJson(Map<String, dynamic> json) =>
    QuestionsResponse(
      available: json['available'] as bool,
      model: json['model'] as String,
      maxContextChars: (json['max_context_chars'] as num).toInt(),
      questions: (json['questions'] as List<dynamic>)
          .map((e) => ExplainQuestion.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

const _$QuestionsResponseFieldMap = <String, String>{
  'available': 'available',
  'model': 'model',
  'maxContextChars': 'max_context_chars',
  'questions': 'questions',
};

Map<String, dynamic> _$QuestionsResponseToJson(QuestionsResponse instance) =>
    <String, dynamic>{
      'available': instance.available,
      'model': instance.model,
      'max_context_chars': instance.maxContextChars,
      'questions': instance.questions.map((e) => e.toJson()).toList(),
    };

ExplainResponse _$ExplainResponseFromJson(Map<String, dynamic> json) =>
    ExplainResponse(
      text: json['text'] as String,
      model: json['model'] as String,
      cached: json['cached'] as bool,
    );

const _$ExplainResponseFieldMap = <String, String>{
  'text': 'text',
  'model': 'model',
  'cached': 'cached',
};

Map<String, dynamic> _$ExplainResponseToJson(ExplainResponse instance) =>
    <String, dynamic>{
      'text': instance.text,
      'model': instance.model,
      'cached': instance.cached,
    };

SpeechInfoResponse _$SpeechInfoResponseFromJson(Map<String, dynamic> json) =>
    SpeechInfoResponse(
      available: json['available'] as bool,
      model: json['model'] as String,
      languages: (json['languages'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
    );

const _$SpeechInfoResponseFieldMap = <String, String>{
  'available': 'available',
  'model': 'model',
  'languages': 'languages',
};

Map<String, dynamic> _$SpeechInfoResponseToJson(SpeechInfoResponse instance) =>
    <String, dynamic>{
      'available': instance.available,
      'model': instance.model,
      'languages': instance.languages,
    };

AudioLesson _$AudioLessonFromJson(Map<String, dynamic> json) => AudioLesson(
  number: (json['number'] as num).toInt(),
  title: json['title'] as String,
  audio: $enumDecode(_$AudioStateEnumMap, json['audio']),
  position: (json['position'] as num?)?.toDouble() ?? 0,
  duration: (json['duration'] as num?)?.toDouble() ?? 0,
  finished: json['finished'] as bool? ?? false,
);

const _$AudioLessonFieldMap = <String, String>{
  'number': 'number',
  'title': 'title',
  'audio': 'audio',
  'position': 'position',
  'duration': 'duration',
  'finished': 'finished',
};

Map<String, dynamic> _$AudioLessonToJson(AudioLesson instance) =>
    <String, dynamic>{
      'number': instance.number,
      'title': instance.title,
      'audio': _$AudioStateEnumMap[instance.audio]!,
      'position': instance.position,
      'duration': instance.duration,
      'finished': instance.finished,
    };

const _$AudioStateEnumMap = {
  AudioState.ready: 'ready',
  AudioState.stale: 'stale',
  AudioState.none: 'none',
};

AudioCourse _$AudioCourseFromJson(Map<String, dynamic> json) => AudioCourse(
  id: json['id'] as String,
  name: json['name'] as String,
  language: json['language'] as String,
  lessons: (json['lessons'] as List<dynamic>)
      .map((e) => AudioLesson.fromJson(e as Map<String, dynamic>))
      .toList(),
);

const _$AudioCourseFieldMap = <String, String>{
  'id': 'id',
  'name': 'name',
  'language': 'language',
  'lessons': 'lessons',
};

Map<String, dynamic> _$AudioCourseToJson(AudioCourse instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'language': instance.language,
      'lessons': instance.lessons.map((e) => e.toJson()).toList(),
    };

AudioCoursesResponse _$AudioCoursesResponseFromJson(
  Map<String, dynamic> json,
) => AudioCoursesResponse(
  courses: (json['courses'] as List<dynamic>)
      .map((e) => AudioCourse.fromJson(e as Map<String, dynamic>))
      .toList(),
);

const _$AudioCoursesResponseFieldMap = <String, String>{'courses': 'courses'};

Map<String, dynamic> _$AudioCoursesResponseToJson(
  AudioCoursesResponse instance,
) => <String, dynamic>{
  'courses': instance.courses.map((e) => e.toJson()).toList(),
};

AudioLine _$AudioLineFromJson(Map<String, dynamic> json) => AudioLine(
  speaker: $enumDecode(_$SpeakerEnumMap, json['speaker']),
  text: json['text'] as String,
  seconds: (json['seconds'] as num).toDouble(),
);

const _$AudioLineFieldMap = <String, String>{
  'speaker': 'speaker',
  'text': 'text',
  'seconds': 'seconds',
};

Map<String, dynamic> _$AudioLineToJson(AudioLine instance) => <String, dynamic>{
  'speaker': _$SpeakerEnumMap[instance.speaker]!,
  'text': instance.text,
  'seconds': instance.seconds,
};

const _$SpeakerEnumMap = {
  Speaker.narrator: 'narrator',
  Speaker.actor1: 'actor 1',
  Speaker.actor2: 'actor 2',
  Speaker.pause: 'pause',
};

AudioLessonResponse _$AudioLessonResponseFromJson(Map<String, dynamic> json) =>
    AudioLessonResponse(
      title: json['title'] as String,
      summary: json['summary'] as String,
      grammar: json['grammar'] as String,
      lines: (json['lines'] as List<dynamic>)
          .map((e) => AudioLine.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

const _$AudioLessonResponseFieldMap = <String, String>{
  'title': 'title',
  'summary': 'summary',
  'grammar': 'grammar',
  'lines': 'lines',
};

Map<String, dynamic> _$AudioLessonResponseToJson(
  AudioLessonResponse instance,
) => <String, dynamic>{
  'title': instance.title,
  'summary': instance.summary,
  'grammar': instance.grammar,
  'lines': instance.lines.map((e) => e.toJson()).toList(),
};

AudioProgressResponse _$AudioProgressResponseFromJson(
  Map<String, dynamic> json,
) => AudioProgressResponse(
  position: (json['position'] as num).toDouble(),
  duration: (json['duration'] as num).toDouble(),
  finished: json['finished'] as bool,
);

const _$AudioProgressResponseFieldMap = <String, String>{
  'position': 'position',
  'duration': 'duration',
  'finished': 'finished',
};

Map<String, dynamic> _$AudioProgressResponseToJson(
  AudioProgressResponse instance,
) => <String, dynamic>{
  'position': instance.position,
  'duration': instance.duration,
  'finished': instance.finished,
};

const _$ClassifyRequestFieldMap = <String, String>{
  'text': 'text',
  'language': 'language',
  'heavy': 'heavy',
  'nonstandard': 'nonstandard',
  'track': 'track',
  'translate': 'translate',
  'source': 'source',
};

Map<String, dynamic> _$ClassifyRequestToJson(ClassifyRequest instance) =>
    <String, dynamic>{
      'text': instance.text,
      'language': instance.language,
      'heavy': instance.heavy,
      'nonstandard': instance.nonstandard,
      'track': instance.track,
      'translate': instance.translate,
      'source': _$SourceEnumMap[instance.source]!,
    };

const _$AnswerRequestFieldMap = <String, String>{
  'typed': 'typed',
  'heavy': 'heavy',
  'elapsedMs': 'elapsed_ms',
};

Map<String, dynamic> _$AnswerRequestToJson(AnswerRequest instance) =>
    <String, dynamic>{
      'typed': instance.typed,
      'heavy': instance.heavy,
      'elapsed_ms': instance.elapsedMs,
    };

const _$RatingRequestFieldMap = <String, String>{'rating': 'rating'};

Map<String, dynamic> _$RatingRequestToJson(RatingRequest instance) =>
    <String, dynamic>{'rating': instance.rating};

const _$ExplainRequestFieldMap = <String, String>{
  'question': 'question',
  'userContext': 'user_context',
  'locale': 'locale',
};

Map<String, dynamic> _$ExplainRequestToJson(ExplainRequest instance) =>
    <String, dynamic>{
      'question': instance.question,
      'user_context': instance.userContext,
      'locale': instance.locale,
    };

const _$ExplainSentenceRequestFieldMap = <String, String>{
  'question': 'question',
  'userContext': 'user_context',
  'locale': 'locale',
  'text': 'text',
  'language': 'language',
};

Map<String, dynamic> _$ExplainSentenceRequestToJson(
  ExplainSentenceRequest instance,
) => <String, dynamic>{
  'question': instance.question,
  'user_context': instance.userContext,
  'locale': instance.locale,
  'text': instance.text,
  'language': instance.language,
};

const _$AudioProgressRequestFieldMap = <String, String>{
  'position': 'position',
  'duration': 'duration',
};

Map<String, dynamic> _$AudioProgressRequestToJson(
  AudioProgressRequest instance,
) => <String, dynamic>{
  'position': instance.position,
  'duration': instance.duration,
};
