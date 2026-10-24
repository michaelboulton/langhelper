import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/api/models.dart';

import 'fixtures.dart';

/// The schema of each model: Dart field name -> JSON key.
const models = <String, Map<String, String>>{
  'Accent': Accent.fields,
  'ProblemMessage': ProblemMessage.fields,
  'Word': Word.fields,
  'Sentence': Sentence.fields,
  'Translation': Translation.fields,
  'ClassifyResponse': ClassifyResponse.fields,
  'LanguageInfo': LanguageInfo.fields,
  'Locale': Locale.fields,
  'LocalesResponse': LocalesResponse.fields,
  'LanguagesResponse': LanguagesResponse.fields,
  'LoadingModel': LoadingModel.fields,
  'StatusResponse': StatusResponse.fields,
  'Counts': Counts.fields,
  'Deck': Deck.fields,
  'DecksResponse': DecksResponse.fields,
  'Media': Media.fields,
  'NextCard': NextCard.fields,
  'NoCard': NoCard.fields,
  'LinkedAnswer': LinkedAnswer.fields,
  'AnswerResponse': AnswerResponse.fields,
  'RatingResponse': RatingResponse.fields,
  'FlashcardUser': FlashcardUser.fields,
  'UsersResponse': UsersResponse.fields,
  'StatsDay': StatsDay.fields,
  'StatsResponse': StatsResponse.fields,
  'ExplainQuestion': ExplainQuestion.fields,
  'QuestionsResponse': QuestionsResponse.fields,
  'ExplainResponse': ExplainResponse.fields,
  'SpeechInfoResponse': SpeechInfoResponse.fields,
  'AudioLesson': AudioLesson.fields,
  'AudioCourse': AudioCourse.fields,
  'AudioCoursesResponse': AudioCoursesResponse.fields,
  'AudioLine': AudioLine.fields,
  'AudioLessonResponse': AudioLessonResponse.fields,
  'ClassifyRequest': ClassifyRequest.fields,
  'AnswerRequest': AnswerRequest.fields,
  'RatingRequest': RatingRequest.fields,
  'ExplainRequest': ExplainRequest.fields,
  'ExplainSentenceRequest': ExplainSentenceRequest.fields,
};

/// The schemas with no model: ApiException reads the errors, and the page
/// does not read the lemmas.
const others = {
  'ErrorResponse',
  'HTTPValidationError',
  'ValidationError',
  'LemmaCount',
  'LemmasResponse',
};

void main() {
  final schemas =
      (readJson('openapi.json')['components']
              as Map<String, dynamic>)['schemas']
          as Map<String, dynamic>;

  test('each schema has a model, or is in others', () {
    expect(schemas.keys.toSet(), {...models.keys, ...others});
  });

  test('each model has the fields of its schema', () {
    for (final MapEntry(key: name, value: fields) in models.entries) {
      final schema = schemas[name] as Map<String, dynamic>;
      final properties = schema['properties'] as Map<String, dynamic>;
      expect(
        fields.values.toSet(),
        properties.keys.toSet(),
        reason: '$name in lib/api/models.dart',
      );
    }
  });
}
