import 'dart:convert';
import 'dart:io';

/// A saved file of test/api/. flutter test runs in the package folder.
Map<String, dynamic> readJson(String name) =>
    jsonDecode(File('test/api/$name').readAsStringSync())
        as Map<String, dynamic>;

/// A saved response of test/api/samples/.
Map<String, dynamic> sample(String name) => readJson('samples/$name');
