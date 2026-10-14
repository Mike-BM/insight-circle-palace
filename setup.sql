BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 7f0d3b59853a

CREATE TABLE programs (
    id VARCHAR(36) NOT NULL, 
    slug VARCHAR NOT NULL, 
    title VARCHAR NOT NULL, 
    description TEXT, 
    path VARCHAR, 
    is_active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_programs_slug ON programs (slug);

CREATE TABLE users (
    id VARCHAR(36) NOT NULL, 
    email VARCHAR NOT NULL, 
    password_hash VARCHAR NOT NULL, 
    full_name VARCHAR NOT NULL, 
    phone VARCHAR, 
    country VARCHAR, 
    role VARCHAR NOT NULL, 
    email_verified BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    status VARCHAR NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE applications (
    id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    q1_curiosity TEXT, 
    q2_awareness TEXT, 
    q3_mindset TEXT, 
    q4_reflection TEXT, 
    q5_focus TEXT, 
    assigned_path VARCHAR, 
    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE email_verification_tokens (
    id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    token_hash VARCHAR NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    used_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE enrollments (
    id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    program_id VARCHAR(36) NOT NULL, 
    status VARCHAR NOT NULL, 
    enrolled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(program_id) REFERENCES programs (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    CONSTRAINT uix_user_program UNIQUE (user_id, program_id)
);

CREATE TABLE modules (
    id VARCHAR(36) NOT NULL, 
    program_id VARCHAR(36) NOT NULL, 
    title VARCHAR NOT NULL, 
    "order" INTEGER NOT NULL, 
    content_url VARCHAR, 
    description TEXT, 
    PRIMARY KEY (id), 
    FOREIGN KEY(program_id) REFERENCES programs (id)
);

CREATE TABLE password_reset_tokens (
    id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    token_hash VARCHAR NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    used_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE sessions (
    id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    token_hash VARCHAR NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    ip_address VARCHAR, 
    user_agent VARCHAR, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE certificates (
    id VARCHAR(36) NOT NULL, 
    enrollment_id VARCHAR(36) NOT NULL, 
    user_id VARCHAR(36) NOT NULL, 
    program_id VARCHAR(36) NOT NULL, 
    certificate_number VARCHAR NOT NULL, 
    issued_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    pdf_url VARCHAR NOT NULL, 
    verification_code VARCHAR NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(enrollment_id) REFERENCES enrollments (id), 
    FOREIGN KEY(program_id) REFERENCES programs (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    UNIQUE (certificate_number), 
    UNIQUE (enrollment_id), 
    UNIQUE (verification_code)
);

CREATE TABLE module_completions (
    id VARCHAR(36) NOT NULL, 
    enrollment_id VARCHAR(36) NOT NULL, 
    module_id VARCHAR(36) NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(enrollment_id) REFERENCES enrollments (id), 
    FOREIGN KEY(module_id) REFERENCES modules (id), 
    CONSTRAINT uix_enrollment_module UNIQUE (enrollment_id, module_id)
);

INSERT INTO alembic_version (version_num) VALUES ('7f0d3b59853a') RETURNING alembic_version.version_num;

-- Running upgrade 7f0d3b59853a -> 7576d610eca3

ALTER TABLE users ADD COLUMN photo_url VARCHAR;

ALTER TABLE users ADD COLUMN education_level VARCHAR;

ALTER TABLE users ADD COLUMN bio TEXT;

UPDATE alembic_version SET version_num='7576d610eca3' WHERE alembic_version.version_num = '7f0d3b59853a';

-- Running upgrade 7576d610eca3 -> debafcd77709

CREATE TABLE analytics_events (
    id VARCHAR(36) NOT NULL, 
    event_type VARCHAR NOT NULL, 
    path VARCHAR NOT NULL, 
    user_id VARCHAR(36), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    metadata_json TEXT, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

UPDATE alembic_version SET version_num='debafcd77709' WHERE alembic_version.version_num = '7576d610eca3';


INSERT INTO users (id, email, password_hash, full_name, role, status, email_verified, created_at) VALUES ('68a13ab4-ce18-4460-bb16-284fa5bc22f0', 'admin@insightcircle.com', '$2b$12$94zO7Vc8JWsDOwL1WyauJeHSEraYp975M7rDmnEEuUi0o.2hNgQy.', 'Admin User', 'admin', 'active', true, '2026-08-19T12:41:43.517845');

COMMIT;
