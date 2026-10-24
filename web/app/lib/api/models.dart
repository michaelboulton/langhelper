// The response models of tlhelper/schemas.py that the page reads, and the
// request bodies of the routes. The descriptions of the fields are there.
// After a change, run `dart run build_runner build` (web/README.md, "The API
// client and the models").
import 'package:json_annotation/json_annotation.dart';

part 'models.g.dart';

// The breakdown of a text

@JsonSerializable()
class Accent {
  const Accent({
    required this.form,
    required this.exact,
    this.ambiguous = false,
    this.clitic = false,
  });

  factory Accent.fromJson(Map<String, dynamic> json) => _$AccentFromJson(json);
  Map<String, dynamic> toJson() => _$AccentToJson(this);
  static const fields = _$AccentFieldMap;

  final String form;
  final bool exact;
  final bool ambiguous;
  final bool clitic;
}

@JsonSerializable()
class ProblemMessage {
  const ProblemMessage({required this.key, required this.params});

  factory ProblemMessage.fromJson(Map<String, dynamic> json) =>
      _$ProblemMessageFromJson(json);
  Map<String, dynamic> toJson() => _$ProblemMessageToJson(this);
  static const fields = _$ProblemMessageFieldMap;

  /// The id of a message of the catalogs.
  final String key;

  /// A value is a String, an int or a List of String.
  final Map<String, Object> params;
}

@JsonSerializable()
class Word {
  const Word({
    required this.id,
    required this.text,
    required this.lemma,
    required this.upos,
    required this.xpos,
    required this.feats,
    this.head = 0,
    this.deprel = '',
    required this.startChar,
    required this.endChar,
    this.problems = const [],
    this.problemMessages = const [],
    this.accent,
    this.reading = '',
    this.seen,
  });

  factory Word.fromJson(Map<String, dynamic> json) => _$WordFromJson(json);
  Map<String, dynamic> toJson() => _$WordToJson(this);
  static const fields = _$WordFieldMap;

  final int id;
  final String text;
  final String lemma;
  final String upos;
  final String xpos;
  final Map<String, String> feats;
  final int head;
  final String deprel;
  final int startChar;
  final int endChar;
  final List<String> problems;
  final List<ProblemMessage?> problemMessages;
  final Accent? accent;
  final String reading;
  final int? seen;
}

@JsonSerializable()
class Sentence {
  const Sentence({required this.text, required this.words});

  factory Sentence.fromJson(Map<String, dynamic> json) =>
      _$SentenceFromJson(json);
  Map<String, dynamic> toJson() => _$SentenceToJson(this);
  static const fields = _$SentenceFieldMap;

  final String text;
  final List<Word> words;
}

/// A pair [word of the study language, English word] of `links` or
/// `guesses`.
class Link {
  const Link(this.study, this.english);

  factory Link.fromJson(List<dynamic> json) =>
      Link(json[0] as int, json[1] as int);
  List<int> toJson() => [study, english];

  final int study;
  final int english;
}

/// The links of the two sides: Translation and LinkedAnswer.
abstract class Links {
  const Links({this.links = const [], this.guesses = const []});

  final List<Link> links;
  final List<Link> guesses;
}

@JsonSerializable()
class Translation extends Links {
  const Translation({
    super.links,
    super.guesses,
    this.text = '',
    this.sentences = const [],
    this.error = '',
    this.errorCode = '',
    this.errorParams = const {},
  });

  factory Translation.fromJson(Map<String, dynamic> json) =>
      _$TranslationFromJson(json);
  Map<String, dynamic> toJson() => _$TranslationToJson(this);
  static const fields = _$TranslationFieldMap;

  final String text;
  final List<Sentence> sentences;
  final String error;
  final String errorCode;
  final Map<String, Object> errorParams;
}

enum Source { study, en }

@JsonSerializable()
class ClassifyResponse {
  const ClassifyResponse({
    required this.type,
    required this.language,
    required this.source,
    required this.text,
    required this.sentences,
    this.translation,
  });

  factory ClassifyResponse.fromJson(Map<String, dynamic> json) =>
      _$ClassifyResponseFromJson(json);
  Map<String, dynamic> toJson() => _$ClassifyResponseToJson(this);
  static const fields = _$ClassifyResponseFieldMap;

  final String type;
  final String language;
  final Source source;
  final String text;
  final List<Sentence> sentences;
  final Translation? translation;
}

/// The direction of a script. Not TextDirection, the name of the Flutter
/// type.
enum ScriptDirection { ltr, rtl }

/// A (label, address) entry of LanguageInfo.dictionaryLinks.
class DictionaryLink {
  const DictionaryLink(this.label, this.address);

  factory DictionaryLink.fromJson(List<dynamic> json) =>
      DictionaryLink(json[0] as String, json[1] as String);
  List<String> toJson() => [label, address];

  final String label;
  final String address;
}

@JsonSerializable()
class LanguageInfo {
  const LanguageInfo({
    required this.code,
    required this.name,
    required this.tagName,
    required this.placeholder,
    required this.variants,
    required this.lightNote,
    required this.hasAccents,
    required this.direction,
    required this.speech,
    required this.dictionaryLinks,
    this.uiLocale = '',
    this.nativeName = '',
  });

  factory LanguageInfo.fromJson(Map<String, dynamic> json) =>
      _$LanguageInfoFromJson(json);
  Map<String, dynamic> toJson() => _$LanguageInfoToJson(this);
  static const fields = _$LanguageInfoFieldMap;

  final String code;
  final String name;
  final String tagName;
  final String placeholder;
  final List<String> variants;
  final String lightNote;
  final bool hasAccents;
  final ScriptDirection direction;
  final String speech;
  final List<DictionaryLink> dictionaryLinks;
  final String uiLocale;
  final String nativeName;
}

@JsonSerializable()
class Locale {
  const Locale({
    required this.code,
    required this.name,
    required this.direction,
  });

  factory Locale.fromJson(Map<String, dynamic> json) => _$LocaleFromJson(json);
  Map<String, dynamic> toJson() => _$LocaleToJson(this);
  static const fields = _$LocaleFieldMap;

  final String code;
  final String name;
  final ScriptDirection direction;
}

@JsonSerializable()
class LocalesResponse {
  const LocalesResponse({required this.defaultCode, required this.locales});

  factory LocalesResponse.fromJson(Map<String, dynamic> json) =>
      _$LocalesResponseFromJson(json);
  Map<String, dynamic> toJson() => _$LocalesResponseToJson(this);
  static const fields = _$LocalesResponseFieldMap;

  // `default` is a keyword of Dart.
  @JsonKey(name: 'default')
  final String defaultCode;
  final List<Locale> locales;
}

@JsonSerializable()
class LanguagesResponse {
  const LanguagesResponse({
    required this.languages,
    required this.english,
    required this.largeByDefault,
  });

  factory LanguagesResponse.fromJson(Map<String, dynamic> json) =>
      _$LanguagesResponseFromJson(json);
  Map<String, dynamic> toJson() => _$LanguagesResponseToJson(this);
  static const fields = _$LanguagesResponseFieldMap;

  final List<LanguageInfo> languages;
  final LanguageInfo english;
  final bool largeByDefault;
}

@JsonSerializable()
class LoadingModel {
  const LoadingModel({required this.language, required this.variant});

  factory LoadingModel.fromJson(Map<String, dynamic> json) =>
      _$LoadingModelFromJson(json);
  Map<String, dynamic> toJson() => _$LoadingModelToJson(this);
  static const fields = _$LoadingModelFieldMap;

  final String language;
  final String variant;
}

@JsonSerializable()
class StatusResponse {
  const StatusResponse({
    required this.loading,
    this.loadingModel,
    required this.loaded,
  });

  factory StatusResponse.fromJson(Map<String, dynamic> json) =>
      _$StatusResponseFromJson(json);
  Map<String, dynamic> toJson() => _$StatusResponseToJson(this);
  static const fields = _$StatusResponseFieldMap;

  final String? loading;
  final LoadingModel? loadingModel;
  final List<String> loaded;
}

// The flashcards

@JsonSerializable()
class Counts {
  const Counts({
    required this.total,
    required this.newCards,
    required this.learning,
    required this.due,
  });

  factory Counts.fromJson(Map<String, dynamic> json) => _$CountsFromJson(json);
  Map<String, dynamic> toJson() => _$CountsToJson(this);
  static const fields = _$CountsFieldMap;

  final int total;
  // `new` is a keyword of Dart.
  @JsonKey(name: 'new')
  final int newCards;
  final int learning;
  final int due;
}

@JsonSerializable()
class Deck {
  const Deck({
    required this.id,
    required this.name,
    required this.language,
    required this.path,
    required this.counts,
  });

  factory Deck.fromJson(Map<String, dynamic> json) => _$DeckFromJson(json);
  Map<String, dynamic> toJson() => _$DeckToJson(this);
  static const fields = _$DeckFieldMap;

  final int id;
  final String name;
  final String language;
  final List<String> path;
  final Counts counts;
}

@JsonSerializable()
class DecksResponse {
  const DecksResponse({required this.decks});

  factory DecksResponse.fromJson(Map<String, dynamic> json) =>
      _$DecksResponseFromJson(json);
  Map<String, dynamic> toJson() => _$DecksResponseToJson(this);
  static const fields = _$DecksResponseFieldMap;

  final List<Deck> decks;
}

enum MediaKind { image, audio }

@JsonSerializable()
class Media {
  const Media({required this.kind, required this.url});

  factory Media.fromJson(Map<String, dynamic> json) => _$MediaFromJson(json);
  Map<String, dynamic> toJson() => _$MediaToJson(this);
  static const fields = _$MediaFieldMap;

  final MediaKind kind;
  final String url;
}

@JsonEnum(fieldRename: FieldRename.snake)
enum CardDirection { toStudy, toEnglish, listen, dictation }

/// The answer of GET /api/v1/decks/{id}/next: a NextCard, or a NoCard when
/// the user is through for now.
sealed class NextResult {
  const NextResult();

  factory NextResult.fromJson(Map<String, dynamic> json) =>
      json['done'] == true ? NoCard.fromJson(json) : NextCard.fromJson(json);

  Counts get counts;
}

@JsonSerializable()
class NextCard extends NextResult {
  const NextCard({
    required this.cardId,
    required this.direction,
    required this.language,
    required this.prompt,
    required this.media,
    required this.promptSentences,
    required this.counts,
  });

  factory NextCard.fromJson(Map<String, dynamic> json) =>
      _$NextCardFromJson(json);
  Map<String, dynamic> toJson() => _$NextCardToJson(this);
  static const fields = _$NextCardFieldMap;

  final int cardId;
  final CardDirection direction;
  final String language;
  final String prompt;
  final List<Media> media;
  final List<Sentence> promptSentences;
  @override
  final Counts counts;
}

@JsonSerializable()
class NoCard extends NextResult {
  const NoCard({this.done = true, required this.nextDue, required this.counts});

  factory NoCard.fromJson(Map<String, dynamic> json) => _$NoCardFromJson(json);
  Map<String, dynamic> toJson() => _$NoCardToJson(this);
  static const fields = _$NoCardFieldMap;

  final bool done;
  final String? nextDue;
  @override
  final Counts counts;
}

@JsonSerializable()
class LinkedAnswer extends Links {
  const LinkedAnswer({super.links, super.guesses, required this.sentences});

  factory LinkedAnswer.fromJson(Map<String, dynamic> json) =>
      _$LinkedAnswerFromJson(json);
  Map<String, dynamic> toJson() => _$LinkedAnswerToJson(this);
  static const fields = _$LinkedAnswerFieldMap;

  final List<Sentence> sentences;
}

enum DiffOp { equal, delete, insert }

/// An entry [op, text] of AnswerResponse.diff.
class DiffSpan {
  const DiffSpan(this.op, this.text);

  factory DiffSpan.fromJson(List<dynamic> json) =>
      DiffSpan(DiffOp.values.byName(json[0] as String), json[1] as String);
  List<String> toJson() => [op.name, text];

  final DiffOp op;
  final String text;
}

@JsonSerializable()
class AnswerResponse {
  const AnswerResponse({
    required this.reviewId,
    required this.rating,
    required this.nextDue,
    required this.diff,
    required this.answers,
    required this.media,
    required this.prompt,
    required this.promptSentences,
    required this.typed,
    required this.correct,
  });

  factory AnswerResponse.fromJson(Map<String, dynamic> json) =>
      _$AnswerResponseFromJson(json);
  Map<String, dynamic> toJson() => _$AnswerResponseToJson(this);
  static const fields = _$AnswerResponseFieldMap;

  final int reviewId;
  final int rating;
  final String nextDue;
  final List<DiffSpan> diff;
  final List<String> answers;
  final List<Media> media;
  final String prompt;
  final List<Sentence> promptSentences;
  final LinkedAnswer typed;
  final LinkedAnswer correct;
}

@JsonSerializable()
class RatingResponse {
  const RatingResponse({required this.rating, required this.nextDue});

  factory RatingResponse.fromJson(Map<String, dynamic> json) =>
      _$RatingResponseFromJson(json);
  Map<String, dynamic> toJson() => _$RatingResponseToJson(this);
  static const fields = _$RatingResponseFieldMap;

  final int rating;
  final String nextDue;
}

@JsonSerializable()
class FlashcardUser {
  const FlashcardUser({required this.id, required this.name});

  factory FlashcardUser.fromJson(Map<String, dynamic> json) =>
      _$FlashcardUserFromJson(json);
  Map<String, dynamic> toJson() => _$FlashcardUserToJson(this);
  static const fields = _$FlashcardUserFieldMap;

  final String id;
  final String name;
}

@JsonSerializable()
class UsersResponse {
  const UsersResponse({
    required this.me,
    required this.admin,
    required this.users,
  });

  factory UsersResponse.fromJson(Map<String, dynamic> json) =>
      _$UsersResponseFromJson(json);
  Map<String, dynamic> toJson() => _$UsersResponseToJson(this);
  static const fields = _$UsersResponseFieldMap;

  final String me;
  final bool admin;
  final List<FlashcardUser> users;
}

@JsonSerializable()
class StatsDay {
  const StatsDay({
    required this.date,
    required this.reviews,
    required this.passed,
  });

  factory StatsDay.fromJson(Map<String, dynamic> json) =>
      _$StatsDayFromJson(json);
  Map<String, dynamic> toJson() => _$StatsDayToJson(this);
  static const fields = _$StatsDayFieldMap;

  final String date;
  final int reviews;
  final int passed;
}

// With no deck, `counts` is {}.
Counts? _countsOrNull(Map<String, dynamic> json) =>
    json.isEmpty ? null : Counts.fromJson(json);
Map<String, dynamic> _countsOrEmpty(Counts? counts) => counts?.toJson() ?? {};

@JsonSerializable()
class StatsResponse {
  const StatsResponse({
    required this.counts,
    required this.reviews,
    required this.successRate,
    required this.lapses,
    required this.streakDays,
    required this.days,
  });

  factory StatsResponse.fromJson(Map<String, dynamic> json) =>
      _$StatsResponseFromJson(json);
  Map<String, dynamic> toJson() => _$StatsResponseToJson(this);
  static const fields = _$StatsResponseFieldMap;

  /// Null if there is no deck.
  @JsonKey(fromJson: _countsOrNull, toJson: _countsOrEmpty)
  final Counts? counts;
  final int reviews;
  final double? successRate;
  final int lapses;
  final int streakDays;
  final List<StatsDay> days;
}

// The "explain with AI" buttons

enum QuestionPlace { sentence, card }

@JsonSerializable()
class ExplainQuestion {
  const ExplainQuestion({
    required this.id,
    required this.label,
    required this.where,
  });

  factory ExplainQuestion.fromJson(Map<String, dynamic> json) =>
      _$ExplainQuestionFromJson(json);
  Map<String, dynamic> toJson() => _$ExplainQuestionToJson(this);
  static const fields = _$ExplainQuestionFieldMap;

  final String id;
  final String label;
  final QuestionPlace where;
}

@JsonSerializable()
class QuestionsResponse {
  const QuestionsResponse({
    required this.available,
    required this.model,
    required this.maxContextChars,
    required this.questions,
  });

  factory QuestionsResponse.fromJson(Map<String, dynamic> json) =>
      _$QuestionsResponseFromJson(json);
  Map<String, dynamic> toJson() => _$QuestionsResponseToJson(this);
  static const fields = _$QuestionsResponseFieldMap;

  final bool available;
  final String model;
  final int maxContextChars;
  final List<ExplainQuestion> questions;
}

@JsonSerializable()
class ExplainResponse {
  const ExplainResponse({
    required this.text,
    required this.model,
    required this.cached,
  });

  factory ExplainResponse.fromJson(Map<String, dynamic> json) =>
      _$ExplainResponseFromJson(json);
  Map<String, dynamic> toJson() => _$ExplainResponseToJson(this);
  static const fields = _$ExplainResponseFieldMap;

  final String text;
  final String model;
  final bool cached;
}

@JsonSerializable()
class SpeechInfoResponse {
  const SpeechInfoResponse({
    required this.available,
    required this.model,
    required this.languages,
  });

  factory SpeechInfoResponse.fromJson(Map<String, dynamic> json) =>
      _$SpeechInfoResponseFromJson(json);
  Map<String, dynamic> toJson() => _$SpeechInfoResponseToJson(this);
  static const fields = _$SpeechInfoResponseFieldMap;

  final bool available;
  final String model;
  final List<String> languages;
}

// The audio lessons tab

enum AudioState { ready, stale, none }

@JsonSerializable()
class AudioLesson {
  const AudioLesson({
    required this.number,
    required this.title,
    required this.audio,
  });

  factory AudioLesson.fromJson(Map<String, dynamic> json) =>
      _$AudioLessonFromJson(json);
  Map<String, dynamic> toJson() => _$AudioLessonToJson(this);
  static const fields = _$AudioLessonFieldMap;

  final int number;
  final String title;
  final AudioState audio;
}

@JsonSerializable()
class AudioCourse {
  const AudioCourse({
    required this.id,
    required this.name,
    required this.language,
    required this.lessons,
  });

  factory AudioCourse.fromJson(Map<String, dynamic> json) =>
      _$AudioCourseFromJson(json);
  Map<String, dynamic> toJson() => _$AudioCourseToJson(this);
  static const fields = _$AudioCourseFieldMap;

  final String id;
  final String name;
  final String language;
  final List<AudioLesson> lessons;
}

@JsonSerializable()
class AudioCoursesResponse {
  const AudioCoursesResponse({required this.courses});

  factory AudioCoursesResponse.fromJson(Map<String, dynamic> json) =>
      _$AudioCoursesResponseFromJson(json);
  Map<String, dynamic> toJson() => _$AudioCoursesResponseToJson(this);
  static const fields = _$AudioCoursesResponseFieldMap;

  final List<AudioCourse> courses;
}

enum Speaker {
  narrator,
  @JsonValue('actor 1')
  actor1,
  @JsonValue('actor 2')
  actor2,
  pause,
}

@JsonSerializable()
class AudioLine {
  const AudioLine({
    required this.speaker,
    required this.text,
    required this.seconds,
  });

  factory AudioLine.fromJson(Map<String, dynamic> json) =>
      _$AudioLineFromJson(json);
  Map<String, dynamic> toJson() => _$AudioLineToJson(this);
  static const fields = _$AudioLineFieldMap;

  final Speaker speaker;
  final String text;
  final double seconds;
}

@JsonSerializable()
class AudioLessonResponse {
  const AudioLessonResponse({
    required this.title,
    required this.summary,
    required this.grammar,
    required this.lines,
  });

  factory AudioLessonResponse.fromJson(Map<String, dynamic> json) =>
      _$AudioLessonResponseFromJson(json);
  Map<String, dynamic> toJson() => _$AudioLessonResponseToJson(this);
  static const fields = _$AudioLessonResponseFieldMap;

  final String title;
  final String summary;
  final String grammar;
  final List<AudioLine> lines;
}

// The request bodies

@JsonSerializable(createFactory: false)
class ClassifyRequest {
  const ClassifyRequest({
    required this.text,
    required this.language,
    this.heavy = false,
    this.nonstandard = false,
    this.track = true,
    this.translate = false,
    this.source = Source.study,
  });

  Map<String, dynamic> toJson() => _$ClassifyRequestToJson(this);
  static const fields = _$ClassifyRequestFieldMap;

  final String text;
  final String language;
  final bool heavy;
  final bool nonstandard;
  final bool track;
  final bool translate;
  final Source source;
}

@JsonSerializable(createFactory: false)
class AnswerRequest {
  const AnswerRequest({
    required this.typed,
    this.heavy = false,
    this.elapsedMs,
  });

  Map<String, dynamic> toJson() => _$AnswerRequestToJson(this);
  static const fields = _$AnswerRequestFieldMap;

  final String typed;
  final bool heavy;
  final int? elapsedMs;
}

@JsonSerializable(createFactory: false)
class RatingRequest {
  const RatingRequest({required this.rating});

  Map<String, dynamic> toJson() => _$RatingRequestToJson(this);
  static const fields = _$RatingRequestFieldMap;

  final int rating;
}

@JsonSerializable(createFactory: false)
class ExplainRequest {
  const ExplainRequest({
    required this.question,
    required this.locale,
    this.userContext = '',
  });

  Map<String, dynamic> toJson() => _$ExplainRequestToJson(this);
  static const fields = _$ExplainRequestFieldMap;

  final String question;
  final String userContext;
  final String locale;
}

@JsonSerializable(createFactory: false)
class ExplainSentenceRequest extends ExplainRequest {
  const ExplainSentenceRequest({
    required super.question,
    required super.locale,
    super.userContext,
    required this.text,
    required this.language,
  });

  @override
  Map<String, dynamic> toJson() => _$ExplainSentenceRequestToJson(this);
  static const fields = _$ExplainSentenceRequestFieldMap;

  final String text;
  final String language;
}
