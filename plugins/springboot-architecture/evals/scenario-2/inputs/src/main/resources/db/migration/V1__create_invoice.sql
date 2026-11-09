create sequence invoice_seq start with 1 increment by 50;
create table invoice (id bigint primary key, customer varchar(255) not null, amount numeric(19, 2) not null);
