import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:langhelper_app/api/models.dart';

import 'samples.dart';

/// Each saved response, and its decoder.
final decoders = <String, Object Function(Map<String, dynamic>)>{
  'answer.json': AnswerResponse.fromJson,
  'audio_lesson.json': AudioLessonResponse.fromJson,
  'audio_lessons.json': AudioCoursesResponse.fromJson,
  'classify.json': ClassifyResponse.fromJson,
  'decks.json': DecksResponse.fromJson,
  'explain.json': ExplainResponse.fromJson,
  'languages.json': LanguagesResponse.fromJson,
  'locales.json': LocalesResponse.fromJson,
  'next.json': NextResult.fromJson,
  'next_done.json': NextResult.fromJson,
  'questions.json': QuestionsResponse.fromJson,
  'rating.json': RatingResponse.fromJson,
  'speech.json': SpeechInfoResponse.fromJson,
  'stats.json': StatsResponse.fromJson,
  'status.json': StatusResponse.fromJson,
  'users.json': UsersResponse.fromJson,
};

/// [actual] has each key and value of [expected], and maybe more keys: the
/// fields that the response left out.
void expectHas(Object? actual, Object? expected, String path) {
  if (expected is Map) {
    expect(actual, isA<Map<dynamic, dynamic>>(), reason: path);
    for (final MapEntry(:key, :value) in expected.entries) {
      expectHas((actual as Map)[key], value, '$path.$key');
    }
  } else if (expected is List) {
    expect(actual, isA<List<dynamic>>(), reason: path);
    expect((actual as List).length, expected.length, reason: path);
    for (var i = 0; i < expected.length; i++) {
      expectHas(actual[i], expected[i], '$path[$i]');
    }
  } else {
    expect(actual, expected, reason: path);
  }
}

void main() {
  test('each sample decodes, and toJson gives back each of its values', () {
    final files = Directory('test/api/samples').listSync();
    expect(files.map((file) => file.uri.pathSegments.last).toSet(), {
      ...decoders.keys,
    });
    for (final MapEntry(key: name, value: decode) in decoders.entries) {
      final json = sample(name);
      final decoded = decode(json) as dynamic;
      expectHas(decoded.toJson(), json, name);
    }
  });

  test('a breakdown with a translation', () {
    final result = ClassifyResponse.fromJson(sample('classify.json'));
    expect(result.source, Source.study);
    final words = result.sentences.single.words;
    expect(words.first.text, 'Ona');
    expect(words.first.accent?.form, 'Òna');
    expect(words.last.upos, 'PUNCT');
    expect(words.last.accent, isNull);
    expect(words.last.seen, isNull);
    expect(words.last.reading, '');
    final repeat = words.firstWhere((word) => word.problems.isNotEmpty);
    expect(repeat.problemMessages.single?.key, 'problem-repeat');
    expect(repeat.problemMessages.single?.params, {'words': 'je'});
    final translation = result.translation!;
    expect(translation.text, 'She was at home.');
    expect(translation.links.first.study, 0);
    expect(translation.links.first.english, 0);
    expect(translation.guesses, isNotEmpty);
    expect(translation.error, '');
  });

  test('a translation that failed', () {
    final translation = Translation.fromJson({
      'error': 'DeepL did not answer in time',
      'error_code': 'translator-timeout',
      'error_params': {'service': 'DeepL'},
    });
    expect(translation.sentences, isEmpty);
    expect(translation.links, isEmpty);
    expect(translation.errorParams, {'service': 'DeepL'});
  });

  test('the languages and the locales', () {
    final languages = LanguagesResponse.fromJson(sample('languages.json'));
    final croatian = languages.languages.first;
    expect(croatian.code, 'hr');
    expect(croatian.direction, ScriptDirection.ltr);
    expect(croatian.dictionaryLinks.first.address, contains('{lemma}'));
    expect(languages.english.code, 'en');
    final locales = LocalesResponse.fromJson(sample('locales.json'));
    expect(locales.defaultCode, 'en');
    expect(locales.locales.map((each) => each.code), contains('hr'));
  });

  test('the next card, and no card', () {
    final card = NextResult.fromJson(sample('next.json'));
    expect(card, isA<NextCard>());
    card as NextCard;
    expect(card.direction, CardDirection.toStudy);
    expect(card.promptSentences.single.words, hasLength(4));
    expect(card.counts.newCards, 2);
    final done = NextResult.fromJson(sample('next_done.json'));
    expect(done, isA<NoCard>());
    expect((done as NoCard).nextDue, isNotNull);
  });

  test('an answer', () {
    final answer = AnswerResponse.fromJson(sample('answer.json'));
    expect(answer.diff.map((span) => span.op), [
      DiffOp.equal,
      DiffOp.delete,
      DiffOp.insert,
      DiffOp.equal,
    ]);
    expect(answer.diff[1].text, 'f');
    expect(answer.typed.links, isNotEmpty);
    expect(answer.correct.sentences.single.text, 'Pijem kavu.');
  });

  test('the stats, also with no deck', () {
    final stats = StatsResponse.fromJson(sample('stats.json'));
    expect(stats.counts?.total, 2);
    expect(stats.successRate, 1.0);
    expect(stats.days, hasLength(90));
    final empty = StatsResponse.fromJson({
      ...sample('stats.json'),
      'counts': <String, dynamic>{},
      'success_rate': null,
    });
    expect(empty.counts, isNull);
    expect(empty.successRate, isNull);
    expect(empty.toJson()['counts'], isEmpty);
  });

  test('an audio lesson', () {
    final lesson = AudioLessonResponse.fromJson(sample('audio_lesson.json'));
    expect(lesson.lines.map((line) => line.speaker), [
      Speaker.narrator,
      Speaker.pause,
      Speaker.actor1,
      Speaker.actor2,
    ]);
    expect(lesson.lines[1].seconds, 3);
    final courses = AudioCoursesResponse.fromJson(sample('audio_lessons.json'));
    expect(courses.courses.single.lessons.first.audio, AudioState.none);
  });

  test('the request bodies', () {
    expect(const ClassifyRequest(text: 'Bok', language: 'hr').toJson(), {
      'text': 'Bok',
      'language': 'hr',
      'heavy': false,
      'nonstandard': false,
      'track': true,
      'translate': false,
      'source': 'study',
    });
    expect(
      const ExplainSentenceRequest(
        question: 'meaning',
        locale: 'en',
        text: 'Bok',
        language: 'hr',
      ).toJson(),
      {
        'question': 'meaning',
        'user_context': '',
        'locale': 'en',
        'text': 'Bok',
        'language': 'hr',
      },
    );
    expect(const AnswerRequest(typed: 'kuća', elapsedMs: 900).toJson(), {
      'typed': 'kuća',
      'heavy': false,
      'elapsed_ms': 900,
    });
  });
}
