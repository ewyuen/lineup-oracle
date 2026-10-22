## MODIFIED Requirements

### Requirement: Free-text team news
The service SHALL accept a team-news submission that carries `text` and no player and kind, parse it (see the team-news-parsing capability), and answer with the predicted lineup of the requested club. The text SHALL be at most 100 characters; a longer text SHALL be rejected with 422 and no state change. The response SHALL also carry a `news` object stating the outcome (`applied` or `posted`), and for `applied` the player's name, the player's club and the kind. A submission that carries a player and a kind SHALL keep using the structured path and answer with `news` absent or null.

#### Scenario: Text submission
- **WHEN** a text submission names a player of the club and a kind and the model works
- **THEN** the response is the updated lineup, without that player if the kind is injury or suspension, and `news` says `applied`

#### Scenario: Player of the other club
- **WHEN** a text submission for one club names a status for a player of the other club of the match
- **THEN** the response is the requested club's lineup, `news` names the other club, and the other club's lineup for that session reflects the status

#### Scenario: Posted text
- **WHEN** a text submission names a club and no person
- **THEN** the response is the unchanged lineup and `news` says `posted`

#### Scenario: Rejected text
- **WHEN** the text cannot be parsed, names an unknown person or is rejected
- **THEN** the response is 422 with a message and the lineup, stored news and news log are unchanged

#### Scenario: Text too long
- **WHEN** the text has 101 characters
- **THEN** the response is 422 and nothing changes

## ADDED Requirements

### Requirement: Posting is limited per session
A session SHALL be able to post one line to the news log at most once every 10 seconds. A text submission that would post a line sooner SHALL be rejected with 429 and a message, with no state change and no entry in the log. Applying a status and rejected submissions SHALL NOT count toward the limit, and one session's posts SHALL NOT limit another session.

#### Scenario: Second post too soon
- **WHEN** a session posts a line and posts another 3 seconds later
- **THEN** the second response is 429 and the news log holds only the first

#### Scenario: Post after the interval
- **WHEN** a session posts a line and posts another 11 seconds later
- **THEN** both lines are in the news log

#### Scenario: Other sessions are not limited
- **WHEN** one session has just posted and another session posts
- **THEN** the second post is accepted

#### Scenario: Status lines are not limited
- **WHEN** a session posts a line and then submits a status line at once
- **THEN** the status is applied

### Requirement: Posted lines do not refresh lineups
A poll SHALL return informational entries like other entries, and an informational entry SHALL NOT make the poll report that the displayed club changed.

#### Scenario: Posted line in a poll
- **WHEN** the only new entry for the caller's match and club is an informational entry
- **THEN** the response contains it and says the displayed club did not change
