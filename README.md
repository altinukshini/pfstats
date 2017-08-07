# pfstats

This is a simple Postfix mail log parser I wrote in python that can filter postfix mail log lines based on date, status, sender, and subject.

In my machine (Ubuntu 14.04LTS, 2GB Ram, 2x Intel(R) Xeon(R) CPU E7- 4850  @ 2.00GHz) it processed 5 million lines in 1.2-1.5 mins. Script was run without filtering emails by status (meaning it calculated all: bounced, sent, deferred and rejected) or sender, but I specified the date (not today's date (default)), which means that the script had to combine gziped log lines from two files and then process them.

## Requirements

### Logrotate

Daily logrotate created in this format for postfix logs:

```
/var/log/postfix/*.log {
    rotate 366
    dateext
    daily
    missingok
    notifempty
    compress
    delaycompress
}
```

Example of postfix log directory files:

```
mail.log
mail.log-20170724.gz
mail.log-20170725.gz
mail.log-20170726.gz
mail.log-20170727.gz
mail.log-20170728.gz
mail.log-20170729.gz
mail.log-20170730.gz
mail.log-20170731.gz
mail.log-20170801.gz
mail.log-20170802.gz
mail.log-20170803.gz
mail.log-20170804
```

### Postfix subject message in log

This is a little trick for Postfix, it lets you log the subject, from and to of all the emails postfix sends (or which pass through it if you run it as a relay). It comes in handy when you need to debug an email issue and need to confirm your mailserver has sent the message.

First create the file `/etc/postfix/header_checks` and insert this into it:

```
/^subject:/      WARN
```

Now, in your postfix `/etc/postfix/main.cf` add the following to the end of the file:

```
header_checks = regexp:/etc/postfix/header_checks
```

And restart postfix:
```
$ /etc/init.d/postfix restart
```

You will hopefully now get log items like below, and if not you have a problem with your mailserver:

```
Dec  4 08:23:05 localhost postfix/cleanup[2278]: 90CA714: warning: header Subject: This is a testmail which gets logged from localhost[127.0.0.1]; from=<root@localhost> to=<root@localhost> proto=ESMTP helo=<localhost>
```

## Usage

```
$ pfstats.py -h
```

```
usage: pfstats.py [-h] [-d] [-t] [-s] [-m] [-l] [--log-dir]
                  [--output-directory] [--output-delimiter]
                  [--output-filetype]

Filter and format Postfix log files.

optional arguments:
  -h, --help           show this help message and exit
  -d , --date          Specify different date. Default is current date.
                       Format: Jan 20 (note one space) &
                       Jan  2 (note two spaces).
                       Default is todays date: Aug  7

  -t , --type          Type of email status: bounced, sent, rejected, deferred.
                       Default is all.

  -s , --sender        Specify senders address in order to query logs matching this parameter

  -m , --message       Postfix default log format must be changed for this option to work.
                       Add subject message in logs, and then you can use this option to query
                       those emails with specific subject message.

  -l , --log           Specify the log file you want to use.
                       Default is: /var/log/postfix/mail.log

  --log-dir            Specify the log directory.
                       Default is: /var/log/postfix/

  --output-directory   Specify the generated file(s) directory.
                       Default is current working directory: /home/myuser/pfstats

  --output-delimiter   Specify the generated output delimiter.
                       Default is ";"

  --output-filetype    Specify the generated output file type.
                       Default is "csv"
```

### Example 1

```
$ python pfstats.py -d 'Jul 26' -s 'info@altinukshini.com'


************************* RESULTS *************************

bounced:        5079            bounced-261841.csv
deferred:       2570            deferred-261841.csv
sent:           9397            sent-261841.csv
rejected:       0               rejected-261841.csv

-----
Total:          17046

***********************************************************
--- 69.95447611808777 seconds ---
```

### Example 2

```
$ python pfstats.py -d 'Jul 26' -t 'bounced' -s 'info@altinukshini.com'


************************* RESULTS *************************

bounced:        5079            bounced-882924.csv

-----
Total:          5079

***********************************************************
--- 19.795605659484863 seconds ---
```

### Output Examples

#### Sent

```
date;sender;receiver;message_id;subject;host_message
Jul 26;info@altinukshini.com;example@test.com;96CF641D9A;Hello World;(250 2.6.0 <13105b0f78dc3b52b30bcb42f44b9a66@localhost.localdomain> [InternalId=18245021073525, Hostname=mail.altinukshini.com] 82359 bytes in 0.119, 672.660 KB/sec Queued mail for delivery)
```

#### Bounced

```
date;sender;receiver;message_id;subject;host_message
Jul 26;info@altinukshini.com;testasdf@hotmail.com;9018142B3F;Hello World;(host mx2.hotmail.com[207.46.8.199] said: 550 Requested action not taken: mailbox unavailable (in reply to RCPT TO command))
```