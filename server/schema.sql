-- =============================================================================
-- CINEFOLIO - ESQUEMA DE BANCO DE DADOS (DDL)
-- SGBD: SQLite 3
-- =============================================================================



-- Habilita a checagem de chaves estrangeiras (FOREIGN KEY).
-- No SQLite isso vem DESLIGADO por padrão em cada nova conexão,
-- por isso precisa ser ligado explicitamente aqui.
PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- Tabela: users
-- Armazena os dados cadastrais, credenciais e personalização do perfil.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                                       -- identificador único do usuário
    username TEXT NOT NULL UNIQUE CHECK (length(username) BETWEEN 3 AND 30),        -- nome de login, precisa ser único e entre 3 e 30 caracteres
    display_name TEXT NOT NULL CHECK (length(display_name) BETWEEN 1 AND 80),   -- nome exibido publicamente no perfil
    bio TEXT NOT NULL DEFAULT '' CHECK (length(bio) <= 500),                    -- biografia/descrição do usuário e limite de 500 caracteres
    password_hash TEXT NOT NULL,                                                -- senha JAMAIS armazenada em texto puro, só o hash gerado com salt é guardado
    avatar_url TEXT NOT NULL DEFAULT '',                                        -- caminho/URL da imagem de avatar
    banner_url TEXT NOT NULL DEFAULT '',                                        -- caminho/URL da imagem de capa/banner
    created_at TEXT NOT NULL                                                    -- data/hora de criação da conta (formato ISO)
);

-- -----------------------------------------------------------------------------
-- Tabela: movies
-- Armazena os metadados dos filmes obtidos da TMDB que foram catalogados.
-- Funciona como um "cache" local: cada filme só é gravado aqui na primeira
-- vez que algum usuário interage com ele (favorita, avalia, etc).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                                       -- id interno do Cinefolio
    tmdb_id INTEGER NOT NULL UNIQUE CHECK (tmdb_id > 0),                            -- id do filme na API externa (TMDB)
    title TEXT NOT NULL,                                                        -- título (traduzido/local)
    original_title TEXT NOT NULL DEFAULT '',                                    -- título original (ex: idioma de origem)
    release_year INTEGER                                                        -- ano de lançamento
        CHECK (release_year IS NULL OR release_year BETWEEN 1888 AND 2200),     -- 1888 = ano do filme mais antigo conhecido da história do cinema
    poster_path TEXT NOT NULL DEFAULT '',                                       -- caminho da imagem do pôster
    backdrop_path TEXT NOT NULL DEFAULT '',                                     -- caminho da imagem de fundo/destaque
    created_at TEXT NOT NULL                                                    -- quando o filme foi catalogado no sistema
);

-- -----------------------------------------------------------------------------
-- Tabela: user_movies
-- Tabela associativa (N:M) entre usuários e filmes, com status, avaliação e review.
-- É aqui que fica registrado "o usuário X assistiu/está assistindo o filme Y".
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_movies (                        
    user_id INTEGER NOT NULL,               -- referência ao usuário
    movie_id INTEGER NOT NULL,              -- referência ao filme
    status TEXT NOT NULL CHECK (status IN ('WATCHING', 'WATCHED', 'PLAN_TO_WATCH', 'DROPPED')), -- estado atual do filme na lista do usuário, WATCHING = assistindo | WATCHED = assistido, PLAN_TO_WATCH = pretende assistir | DROPPED = abandonado
    rating REAL CHECK (rating IS NULL OR (rating >= 0 AND rating <= 10)),                       -- nota dada pelo usuário (0 a 10), opcional
    review TEXT CHECK (review IS NULL OR length(review) <= 5000),                               -- resenha/comentário escrito, opcional
    favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),                             -- 1 = favoritado, 0 = não (funciona como boolean)
    watched_at TEXT,                        -- data em que foi marcado como assistido                                                               
    created_at TEXT NOT NULL,               -- quando o registro foi criado
    updated_at TEXT NOT NULL,               -- última vez que o registro foi alterado
    PRIMARY KEY (user_id, movie_id),        -- chave composta: 1 registro por par (usuário, filme)
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,   -- se o usuário for apagado, seus registros de filmes somem junto
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE  -- se o filme for apagado, os registros de usuários relacionados a ele somem junto
);

-- -----------------------------------------------------------------------------
-- Tabela: sessions
-- Armazena os tokens de autenticação das sessões ativas com expiração.
-- Usada para manter o usuário "logado" entre requisições (sistema de login).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,               -- dono da sessão
    token_hash TEXT NOT NULL UNIQUE,        -- hash do token de autenticação (não armazenamos o token em texto puro)        
    expires_at TEXT NOT NULL,               -- data/hora em que a sessão expira
    created_at TEXT NOT NULL,               -- quando a sessão foi criada (login)
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- -----------------------------------------------------------------------------
-- Índices para otimização de consultas frequentes
-- Índices aceleram buscas (SELECT) em troca de um pequeno custo extra
-- em inserções/atualizações. Aqui eles cobrem as consultas mais comuns do app.
-- -----------------------------------------------------------------------------

-- Acelera "listar filmes do usuário X filtrando por status" (ex: todos os WATCHED)
CREATE INDEX IF NOT EXISTS idx_user_movies_status ON user_movies(user_id, status);

-- Acelera "listar filmes favoritos do usuário X"
CREATE INDEX IF NOT EXISTS idx_user_movies_favorite ON user_movies(user_id, favorite);

-- Acelera "listar filmes assistidos do usuário X, do mais recente para o mais antigo"
CREATE INDEX IF NOT EXISTS idx_user_movies_watched_at ON user_movies(user_id, watched_at DESC);

-- Acelera a validação do token de sessão a cada requisição autenticada
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
