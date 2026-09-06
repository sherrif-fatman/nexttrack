type Props = {
  accessible?: boolean;
  rating: number;
  onChange: (rating: number) => void;
};

export default function Rating({
  accessible = false,
  rating,
  onChange,
}: Props) {
  return (
    <div
      className={`rating ${
        accessible ? "ratingAccessible" : ""
      }`}
      aria-label={`Rating ${rating} out of 5`}
    >
      <span className="rateLabel">Rate</span>

      <div className="stars">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            className={
              value <= rating
                ? "star selected"
                : "star"
            }
            onClick={() => onChange(value)}
            aria-label={`${value} star${
              value === 1 ? "" : "s"
            }`}
            aria-pressed={value <= rating}
          >
            ★
          </button>
        ))}
      </div>

      <span className="ratingValue">
        {rating || "–"}/5
      </span>
    </div>
  );
}
