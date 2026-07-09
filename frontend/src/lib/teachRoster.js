/**
 * @typedef {Object} AssignmentCard
 * @property {'class_section' | 'subject_group' | undefined} [target_type]
 * @property {{ id?: number } | undefined} [school]
 * @property {{ id?: number } | null | undefined} [class_section]
 * @property {{ id?: number } | null | undefined} [subject_group]
 */

/**
 * @param {AssignmentCard | null | undefined} card
 * @returns {string | null}
 */
export function rosterPathForAssignment(card) {
  const schoolId = card?.school?.id;
  if (!schoolId) return null;
  if (card?.target_type === 'subject_group' || card?.subject_group?.id) {
    return card?.subject_group?.id ? `/teach/schools/${schoolId}/subject-groups/${card.subject_group.id}/roster` : null;
  }
  if (card?.target_type === 'class_section' || card?.class_section?.id) {
    return card?.class_section?.id ? `/teach/schools/${schoolId}/sections/${card.class_section.id}/roster` : null;
  }
  return null;
}
