import 'package:finance_expert/screens/login_screen.dart';
import 'package:flutter/material.dart';

void main() {
  runApp(const FinanceExpertApp());
}

class FinanceExpertApp extends StatelessWidget {
  const FinanceExpertApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Finance Expert',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0B1221),
      ),
      home: const LoginScreen(),
    );
  }
}
