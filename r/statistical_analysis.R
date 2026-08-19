# Usage:
# Rscript r/statistical_analysis.R data/exports/conversation_metrics_YYYYMMDD_HHMMSS.csv
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("กรุณาระบุ path CSV ที่ export จากระบบ")

df <- read.csv(args[1], fileEncoding = "UTF-8-BOM")
cat("=== Conversation Statistical Summary ===\n")
cat("Rows:", nrow(df), "\n")
cat("\nBy Product:\n")
print(table(df$product_type))

cat("\nFirst Response Time (minutes):\n")
print(summary(df$first_response_minutes))

cat("\nDrop-off rate by product:\n")
print(aggregate(is_dropoff ~ product_type, data=df, FUN=mean))

cat("\nPurchase signal rate by product:\n")
print(aggregate(has_purchase_signal ~ product_type, data=df, FUN=mean))

# Example hypothesis test when both groups have enough observations
spa <- na.omit(df$first_response_minutes[df$product_type == "SPA"])
fnb <- na.omit(df$first_response_minutes[df$product_type == "FNB"])
if (length(spa) >= 2 && length(fnb) >= 2) {
  cat("\nWelch t-test: SPA vs FNB first response time\n")
  print(t.test(spa, fnb))
}
