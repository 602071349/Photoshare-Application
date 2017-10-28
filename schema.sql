CREATE DATABASE photoshare;
USE photoshare;
DROP TABLE Pictures CASCADE;
DROP TABLE Users CASCADE;

CREATE TABLE Users (
    user_id int4  AUTO_INCREMENT,
    email varchar(255) UNIQUE,
    password varchar(255),
	first_name varchar(255),
	last_name varchar(255),
	date_of_birth date,
	gender varchar(20),
	hometown varchar(255),
  CONSTRAINT users_pk PRIMARY KEY (user_id)
);

CREATE TABLE Pictures
(
  picture_id int4  AUTO_INCREMENT,
  album_id int4,
  user_id int4,
  imgdata longblob ,
  caption varchar(255),
  INDEX upid_idx (user_id),
  CONSTRAINT pictures_pk PRIMARY KEY (picture_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (album_id) REFERENCES Albums(album_id)
);

CREATE TABLE Albums
(
	album_id int4 AUTO_INCREMENT,
	name varchar(255),
	user_id int4,
	date_of_creation date,
	PRIMARY KEY (album_id),
	FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

CREATE TABLE Tags
(
	word varchar(255),
	PRIMARY KEY (word)
);

CREATE TABLE Comments
(
	comment_id int4,
	text varchar(500),
	user_id int4,
	picture_id int4,
	date_of_creation date,
	PRIMARY KEY (comment_id),
	FOREIGN KEY (user_id) REFERENCES Users(user_id),
	FOREIGN KEY (picture_id) REFERENCES Pictures(picture_id)
);

CREATE TABLE User_friend
(
	user_id int4,
	friend_id int4,
	PRIMARY KEY (user_id,friend_id),
	FOREIGN KEY (user_id) REFERENCES Users(user_id),
	FOREIGN KEY (friend_id) REFERENCES Users(user_id)
);

CREATE TABLE Photo_tag
(
	picture_id int4,
	word varchar(255),
	PRIMARY KEY (picture_id,word),
	FOREIGN KEY (picture_id) REFERENCES Pictures(picture_id)
	FOREIGN KEY (word) REFERENCES Tags(word)
);


	
	


















INSERT INTO Users (email, password) VALUES ('test@bu.edu', 'test');
INSERT INTO Users (email, password) VALUES ('test1@bu.edu', 'test');
