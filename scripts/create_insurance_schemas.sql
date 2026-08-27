-- Text2SQL: org/person/product/customer/contract 스키마 생성
-- hr.yaml 제외, YAML 기준 MariaDB DDL
-- 실행 예: mariadb -h 127.0.0.1 -P 3308 -u root -p < scripts/create_insurance_schemas.sql

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `org` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `person` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `product` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `customer` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS `contract` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ---------- org.org ----------
DROP TABLE IF EXISTS `org`.`org`;
CREATE TABLE `org`.`org` (
  `org_id` VARCHAR(5) NOT NULL COMMENT '조직ID',
  `org_nm` VARCHAR(100) NULL COMMENT '조직명',
  `channel_cd` VARCHAR(2) NULL COMMENT '채널구분코드',
  `parent_org_id` VARCHAR(5) NULL COMMENT '상위조직ID',
  PRIMARY KEY (`org_id`),
  CONSTRAINT `fk_org_parent` FOREIGN KEY (`parent_org_id`) REFERENCES `org`.`org` (`org_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='조직';

-- ---------- person.person ----------
DROP TABLE IF EXISTS `person`.`person`;
CREATE TABLE `person`.`person` (
  `emp_cd` VARCHAR(8) NOT NULL COMMENT '취급자코드',
  `emp_nm` VARCHAR(100) NULL COMMENT '취급자명',
  `org_id` VARCHAR(5) NULL COMMENT '조직ID',
  `appoint_dt` DATE NULL COMMENT '위촉일자',
  `terminate_dt` DATE NULL COMMENT '해촉일자',
  `enc_res_no` VARCHAR(30) NULL COMMENT '암호화주민번호',
  PRIMARY KEY (`emp_cd`),
  CONSTRAINT `fk_person_org` FOREIGN KEY (`org_id`) REFERENCES `org`.`org` (`org_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='인사';

-- ---------- product.product ----------
DROP TABLE IF EXISTS `product`.`product`;
CREATE TABLE `product`.`product` (
  `prod_cd` VARCHAR(5) NOT NULL COMMENT '상품코드',
  `prod_nm` VARCHAR(200) NULL COMMENT '상품명',
  `sale_start_dt` DATE NULL COMMENT '판매개시일자',
  `sale_end_dt` DATE NULL COMMENT '판매종료일자',
  PRIMARY KEY (`prod_cd`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='상품';

-- ---------- customer.customer ----------
DROP TABLE IF EXISTS `customer`.`customer`;
CREATE TABLE `customer`.`customer` (
  `cust_id` VARCHAR(20) NOT NULL COMMENT '고객ID',
  `cust_nm` VARCHAR(100) NULL COMMENT '고객명',
  `enc_res_no` VARCHAR(30) NULL COMMENT '암호화주민번호',
  `birth_dt` VARCHAR(8) NULL COMMENT '생년월일',
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='고객';

-- ---------- contract.contract ----------
DROP TABLE IF EXISTS `contract`.`contract`;
CREATE TABLE `contract`.`contract` (
  `cont_no` VARCHAR(16) NOT NULL COMMENT '계약번호',
  `cont_dt` DATE NULL COMMENT '계약일자',
  `ins_item_cd` VARCHAR(1) NULL COMMENT '보험종목코드',
  `prod_cd` VARCHAR(5) NULL COMMENT '상품코드',
  `ins_start_dt` DATE NULL COMMENT '보험시기',
  `ins_end_dt` DATE NULL COMMENT '보험종기',
  `cont_status` VARCHAR(2) NULL COMMENT '계약상태',
  `cont_prem` DECIMAL(11,0) NULL COMMENT '계약보험료',
  `guar_prem` DECIMAL(11,0) NULL COMMENT '보장보험료',
  `save_prem` DECIMAL(11,0) NULL COMMENT '적립보험료',
  `recruiter_cd` VARCHAR(8) NULL COMMENT '모집자코드',
  `recruit_org_id` VARCHAR(5) NULL COMMENT '모집조직ID',
  `collector_cd` VARCHAR(8) NULL COMMENT '수금자코드',
  `contractor_id` VARCHAR(20) NULL COMMENT '계약자ID',
  `insured_id` VARCHAR(20) NULL COMMENT '피보험자ID',
  `pmt_type_cd` VARCHAR(2) NULL COMMENT '수납구분코드',
  `status_chg_dt` DATE NULL COMMENT '계약상태변경일자',
  PRIMARY KEY (`cont_no`),
  CONSTRAINT `fk_contract_product` FOREIGN KEY (`prod_cd`) REFERENCES `product`.`product` (`prod_cd`),
  CONSTRAINT `fk_contract_recruiter` FOREIGN KEY (`recruiter_cd`) REFERENCES `person`.`person` (`emp_cd`),
  CONSTRAINT `fk_contract_recruit_org` FOREIGN KEY (`recruit_org_id`) REFERENCES `org`.`org` (`org_id`),
  CONSTRAINT `fk_contract_collector` FOREIGN KEY (`collector_cd`) REFERENCES `person`.`person` (`emp_cd`),
  CONSTRAINT `fk_contract_contractor` FOREIGN KEY (`contractor_id`) REFERENCES `customer`.`customer` (`cust_id`),
  CONSTRAINT `fk_contract_insured` FOREIGN KEY (`insured_id`) REFERENCES `customer`.`customer` (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='계약';

SET FOREIGN_KEY_CHECKS = 1;

-- 확인
SHOW DATABASES LIKE 'org';
SHOW DATABASES LIKE 'person';
SHOW DATABASES LIKE 'product';
SHOW DATABASES LIKE 'customer';
SHOW DATABASES LIKE 'contract';
SHOW TABLES FROM `org`;
SHOW TABLES FROM `person`;
SHOW TABLES FROM `product`;
SHOW TABLES FROM `customer`;
SHOW TABLES FROM `contract`;
