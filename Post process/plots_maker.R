df2 <- data.frame(Sentiment=rep(c("Good", "Evil"), each=2),
                  Bots=rep(c("Good bot", "Evil bot"),2),
                  Amount=c(16, 2, 1, 19))

# Stacked barplot with multiple groups
ggplot(data=df2, aes(x=Bots, y=Amount, fill=Sentiment)) +
  geom_bar(stat="identity")
# Use position=position_dodge()
ggplot(data=df2, aes(x=Bots, y=Amount, fill=Sentiment)) +
  geom_bar(stat="identity", position=position_dodge()) +
  labs(title="Barplot of the amount of users that voted per bot")


TeaTasting <-
  matrix(c(19, 2, 1, 16),
         nrow = 2,
         dimnames = list(Guess = c("good", "evil"),
                         Truth = c("good bot", "evil bot")))
fisher.test(TeaTasting, alternative = "greater")

df2 <- data.frame(supp=rep(c("VC", "OJ"), each=3),
                  dose=rep(c("D0.5", "D1", "D2"),2),
                  len=c(6.8, 15, 33, 4.2, 10, 29.5))


df2 <- data.frame(Sentiment=rep(c("Positive", "Neutral", "Negative"), each=2),
                  Dataset=rep(c("Positive dataset", "Negative dataset"),3),
                  Samples=c(255310, 74860, 227722, 122793, 83086, 91494))

ggplot(data=df2, aes(x=Dataset, y=Samples, fill=Sentiment)) +
  geom_bar(stat="identity", position=position_dodge()) +
  labs(title="Barplot of the distribution of the sentiment scores from the questions")
