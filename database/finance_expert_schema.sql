-- MySQL dump 10.13  Distrib 8.4.13, for Linux (x86_64)
--
-- Host: localhost    Database: finance_expert
-- ------------------------------------------------------
-- Server version	8.4.13

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `analyses`
--

DROP TABLE IF EXISTS `analyses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `analyses` (
  `analysis_id` varchar(255) NOT NULL,
  `news_id` varchar(191) NOT NULL,
  `schema_version` varchar(20) NOT NULL,
  `model` varchar(100) NOT NULL,
  `prompt_version` varchar(100) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `summary` text NOT NULL,
  `disclaimer` text,
  PRIMARY KEY (`analysis_id`),
  KEY `news_id` (`news_id`),
  CONSTRAINT `analyses_ibfk_1` FOREIGN KEY (`news_id`) REFERENCES `news` (`news_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `analysis_impacts`
--

DROP TABLE IF EXISTS `analysis_impacts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `analysis_impacts` (
  `analysis_id` varchar(255) NOT NULL,
  `symbol` varchar(15) NOT NULL,
  `direction` enum('positive','negative','neutral','uncertain') NOT NULL,
  `confidence` decimal(4,3) NOT NULL,
  `reason` text NOT NULL,
  PRIMARY KEY (`analysis_id`,`symbol`),
  KEY `symbol` (`symbol`),
  CONSTRAINT `analysis_impacts_ibfk_1` FOREIGN KEY (`analysis_id`) REFERENCES `analyses` (`analysis_id`),
  CONSTRAINT `analysis_impacts_ibfk_2` FOREIGN KEY (`symbol`) REFERENCES `stocks` (`symbol`),
  CONSTRAINT `chk_confidence` CHECK (((`confidence` >= 0) and (`confidence` <= 1)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `news`
--

DROP TABLE IF EXISTS `news`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `news` (
  `news_id` varchar(191) NOT NULL,
  `source` enum('KAP','BLOOMBERG_HT') NOT NULL,
  `source_id` varchar(191) DEFAULT NULL,
  `title` text NOT NULL,
  `summary` text,
  `url` text NOT NULL,
  `published_at` datetime(6) DEFAULT NULL,
  `fetched_at` datetime(6) NOT NULL,
  `disclosure_type` varchar(100) DEFAULT NULL,
  `matched_keywords` json NOT NULL,
  PRIMARY KEY (`news_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `news_stocks`
--

DROP TABLE IF EXISTS `news_stocks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `news_stocks` (
  `news_id` varchar(191) NOT NULL,
  `symbol` varchar(15) NOT NULL,
  PRIMARY KEY (`news_id`,`symbol`),
  KEY `symbol` (`symbol`),
  CONSTRAINT `news_stocks_ibfk_1` FOREIGN KEY (`news_id`) REFERENCES `news` (`news_id`),
  CONSTRAINT `news_stocks_ibfk_2` FOREIGN KEY (`symbol`) REFERENCES `stocks` (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `positions`
--

DROP TABLE IF EXISTS `positions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `positions` (
  `position_id` bigint NOT NULL AUTO_INCREMENT,
  `wallet_id` bigint NOT NULL,
  `symbol` varchar(15) NOT NULL,
  `quantity` decimal(18,6) NOT NULL DEFAULT '0.000000',
  `average_cost` decimal(18,6) NOT NULL DEFAULT '0.000000',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`position_id`),
  UNIQUE KEY `uq_wallet_stock` (`wallet_id`,`symbol`),
  KEY `symbol` (`symbol`),
  CONSTRAINT `positions_ibfk_1` FOREIGN KEY (`wallet_id`) REFERENCES `wallets` (`wallet_id`),
  CONSTRAINT `positions_ibfk_2` FOREIGN KEY (`symbol`) REFERENCES `stocks` (`symbol`),
  CONSTRAINT `chk_position_cost` CHECK ((`average_cost` >= 0)),
  CONSTRAINT `chk_position_quantity` CHECK ((`quantity` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `quotes`
--

DROP TABLE IF EXISTS `quotes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `quotes` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `symbol` varchar(15) NOT NULL,
  `price` decimal(18,6) NOT NULL,
  `currency` char(3) NOT NULL DEFAULT 'TRY',
  `as_of` datetime(6) NOT NULL,
  `provider` varchar(100) NOT NULL,
  `is_delayed` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_quote` (`symbol`,`provider`,`as_of`),
  CONSTRAINT `quotes_ibfk_1` FOREIGN KEY (`symbol`) REFERENCES `stocks` (`symbol`),
  CONSTRAINT `chk_quote_price` CHECK ((`price` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stocks`
--

DROP TABLE IF EXISTS `stocks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stocks` (
  `symbol` varchar(15) NOT NULL,
  `company_name` varchar(150) NOT NULL,
  `market` varchar(30) NOT NULL DEFAULT 'BIST',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `trades`
--

DROP TABLE IF EXISTS `trades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trades` (
  `trade_id` bigint NOT NULL AUTO_INCREMENT,
  `wallet_id` bigint NOT NULL,
  `symbol` varchar(15) NOT NULL,
  `side` enum('BUY','SELL') NOT NULL,
  `quantity` decimal(18,6) NOT NULL,
  `price` decimal(18,6) NOT NULL,
  `total_amount` decimal(18,2) NOT NULL,
  `realized_pnl` decimal(18,2) NOT NULL DEFAULT '0.00',
  `executed_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`trade_id`),
  KEY `wallet_id` (`wallet_id`),
  KEY `symbol` (`symbol`),
  CONSTRAINT `trades_ibfk_1` FOREIGN KEY (`wallet_id`) REFERENCES `wallets` (`wallet_id`),
  CONSTRAINT `trades_ibfk_2` FOREIGN KEY (`symbol`) REFERENCES `stocks` (`symbol`),
  CONSTRAINT `chk_trade_price` CHECK ((`price` > 0)),
  CONSTRAINT `chk_trade_quantity` CHECK ((`quantity` > 0)),
  CONSTRAINT `chk_trade_total` CHECK ((`total_amount` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `full_name` varchar(100) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wallets`
--

DROP TABLE IF EXISTS `wallets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wallets` (
  `wallet_id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `currency` char(3) NOT NULL DEFAULT 'TRY',
  `cash_balance` decimal(18,2) NOT NULL DEFAULT '100000.00',
  `realized_pnl` decimal(18,2) NOT NULL DEFAULT '0.00',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`wallet_id`),
  UNIQUE KEY `uq_wallet_user` (`user_id`),
  CONSTRAINT `wallets_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_wallet_balance` CHECK ((`cash_balance` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-24 10:39:41
