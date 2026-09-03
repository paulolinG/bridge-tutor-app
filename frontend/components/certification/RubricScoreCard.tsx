import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { RubricScore } from "@/lib/types/certification";

const CATEGORIES: {
  key: keyof Pick<
    RubricScore,
    | "subject_knowledge"
    | "instructional_quality"
    | "pedagogical_adaptability"
    | "organization"
  >;
  rationaleKey: keyof RubricScore;
  label: string;
  max: number;
}[] = [
  {
    key: "subject_knowledge",
    rationaleKey: "subject_knowledge_rationale",
    label: "Subject knowledge",
    max: 20,
  },
  {
    key: "instructional_quality",
    rationaleKey: "instructional_quality_rationale",
    label: "Instructional quality",
    max: 40,
  },
  {
    key: "pedagogical_adaptability",
    rationaleKey: "pedagogical_adaptability_rationale",
    label: "Pedagogical adaptability",
    max: 20,
  },
  {
    key: "organization",
    rationaleKey: "organization_rationale",
    label: "Organization",
    max: 20,
  },
];

export function RubricScoreCard({ score }: { score: RubricScore }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>
          {score.total_score} / 100
        </CardTitle>
        <Badge variant={score.passed ? "default" : "destructive"}>
          {score.passed ? "Passed" : "Not yet passed"}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {CATEGORIES.map((category, index) => (
          <div key={category.key}>
            {index > 0 && <Separator className="mb-4" />}
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-medium">{category.label}</span>
              <span className="text-sm text-muted-foreground">
                {score[category.key]} / {category.max}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {score[category.rationaleKey] as string}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
