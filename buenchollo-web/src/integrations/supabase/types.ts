export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5";
  };
  public: {
    Tables: {
      alerts: {
        Row: {
          brand: string | null;
          category_id: string | null;
          created_at: string;
          frequency: Database["public"]["Enums"]["alert_frequency"];
          id: string;
          is_active: boolean;
          keyword: string | null;
          last_triggered_at: string | null;
          max_price: number | null;
          min_discount: number | null;
          min_price: number | null;
          name: string;
          notify_email: boolean;
          notify_in_app: boolean;
          store_id: string | null;
          updated_at: string;
          user_id: string;
        };
        Insert: {
          brand?: string | null;
          category_id?: string | null;
          created_at?: string;
          frequency?: Database["public"]["Enums"]["alert_frequency"];
          id?: string;
          is_active?: boolean;
          keyword?: string | null;
          last_triggered_at?: string | null;
          max_price?: number | null;
          min_discount?: number | null;
          min_price?: number | null;
          name: string;
          notify_email?: boolean;
          notify_in_app?: boolean;
          store_id?: string | null;
          updated_at?: string;
          user_id: string;
        };
        Update: {
          brand?: string | null;
          category_id?: string | null;
          created_at?: string;
          frequency?: Database["public"]["Enums"]["alert_frequency"];
          id?: string;
          is_active?: boolean;
          keyword?: string | null;
          last_triggered_at?: string | null;
          max_price?: number | null;
          min_discount?: number | null;
          min_price?: number | null;
          name?: string;
          notify_email?: boolean;
          notify_in_app?: boolean;
          store_id?: string | null;
          updated_at?: string;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "alerts_category_id_fkey";
            columns: ["category_id"];
            isOneToOne: false;
            referencedRelation: "categories";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "alerts_store_id_fkey";
            columns: ["store_id"];
            isOneToOne: false;
            referencedRelation: "stores";
            referencedColumns: ["id"];
          },
        ];
      };
      categories: {
        Row: {
          created_at: string;
          description: string | null;
          display_order: number;
          icon: string | null;
          id: string;
          is_active: boolean;
          name: string;
          parent_id: string | null;
          slug: string;
          updated_at: string;
        };
        Insert: {
          created_at?: string;
          description?: string | null;
          display_order?: number;
          icon?: string | null;
          id?: string;
          is_active?: boolean;
          name: string;
          parent_id?: string | null;
          slug: string;
          updated_at?: string;
        };
        Update: {
          created_at?: string;
          description?: string | null;
          display_order?: number;
          icon?: string | null;
          id?: string;
          is_active?: boolean;
          name?: string;
          parent_id?: string | null;
          slug?: string;
          updated_at?: string;
        };
        Relationships: [
          {
            foreignKeyName: "categories_parent_id_fkey";
            columns: ["parent_id"];
            isOneToOne: false;
            referencedRelation: "categories";
            referencedColumns: ["id"];
          },
        ];
      };
      comment_votes: {
        Row: {
          comment_id: string;
          created_at: string;
          id: string;
          user_id: string;
          vote: number;
        };
        Insert: {
          comment_id: string;
          created_at?: string;
          id?: string;
          user_id: string;
          vote: number;
        };
        Update: {
          comment_id?: string;
          created_at?: string;
          id?: string;
          user_id?: string;
          vote?: number;
        };
        Relationships: [
          {
            foreignKeyName: "comment_votes_comment_id_fkey";
            columns: ["comment_id"];
            isOneToOne: false;
            referencedRelation: "deal_comments";
            referencedColumns: ["id"];
          },
        ];
      };
      deal_comments: {
        Row: {
          content: string;
          created_at: string;
          deal_id: string;
          id: string;
          parent_id: string | null;
          updated_at: string;
          user_id: string;
          votes_down: number;
          votes_up: number;
        };
        Insert: {
          content: string;
          created_at?: string;
          deal_id: string;
          id?: string;
          parent_id?: string | null;
          updated_at?: string;
          user_id: string;
          votes_down?: number;
          votes_up?: number;
        };
        Update: {
          content?: string;
          created_at?: string;
          deal_id?: string;
          id?: string;
          parent_id?: string | null;
          updated_at?: string;
          user_id?: string;
          votes_down?: number;
          votes_up?: number;
        };
        Relationships: [
          {
            foreignKeyName: "deal_comments_deal_id_fkey";
            columns: ["deal_id"];
            isOneToOne: false;
            referencedRelation: "deals";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "deal_comments_parent_id_fkey";
            columns: ["parent_id"];
            isOneToOne: false;
            referencedRelation: "deal_comments";
            referencedColumns: ["id"];
          },
        ];
      };
      deal_votes: {
        Row: {
          created_at: string;
          deal_id: string;
          id: string;
          user_id: string;
          vote: number;
        };
        Insert: {
          created_at?: string;
          deal_id: string;
          id?: string;
          user_id: string;
          vote: number;
        };
        Update: {
          created_at?: string;
          deal_id?: string;
          id?: string;
          user_id?: string;
          vote?: number;
        };
        Relationships: [
          {
            foreignKeyName: "deal_votes_deal_id_fkey";
            columns: ["deal_id"];
            isOneToOne: false;
            referencedRelation: "deals";
            referencedColumns: ["id"];
          },
        ];
      };
      deals: {
        Row: {
          affiliate_url: string;
          brand: string | null;
          category_id: string | null;
          click_count: number;
          comment_count: number;
          created_at: string;
          created_by: string | null;
          current_price: number;
          description: string | null;
          discount_percentage: number | null;
          duplicate_hash: string | null;
          expires_at: string | null;
          external_id: string | null;
          favorite_count: number;
          id: string;
          image_url: string | null;
          images: string[];
          previous_price: number | null;
          published_at: string;
          savings_amount: number | null;
          scheduled_for: string | null;
          shipping_info: string | null;
          short_description: string | null;
          slug: string;
          source: Database["public"]["Enums"]["deal_source"];
          source_url: string | null;
          status: Database["public"]["Enums"]["deal_status"];
          store_id: string | null;
          subcategory_id: string | null;
          temperature: number;
          title: string;
          updated_at: string;
          votes_down: number;
          votes_up: number;
        };
        Insert: {
          affiliate_url: string;
          brand?: string | null;
          category_id?: string | null;
          click_count?: number;
          comment_count?: number;
          created_at?: string;
          created_by?: string | null;
          current_price: number;
          description?: string | null;
          discount_percentage?: number | null;
          duplicate_hash?: string | null;
          expires_at?: string | null;
          external_id?: string | null;
          favorite_count?: number;
          id?: string;
          image_url?: string | null;
          images?: string[];
          previous_price?: number | null;
          published_at?: string;
          savings_amount?: number | null;
          scheduled_for?: string | null;
          shipping_info?: string | null;
          short_description?: string | null;
          slug: string;
          source?: Database["public"]["Enums"]["deal_source"];
          source_url?: string | null;
          status?: Database["public"]["Enums"]["deal_status"];
          store_id?: string | null;
          subcategory_id?: string | null;
          temperature?: number;
          title: string;
          updated_at?: string;
          votes_down?: number;
          votes_up?: number;
        };
        Update: {
          affiliate_url?: string;
          brand?: string | null;
          category_id?: string | null;
          click_count?: number;
          comment_count?: number;
          created_at?: string;
          created_by?: string | null;
          current_price?: number;
          description?: string | null;
          discount_percentage?: number | null;
          duplicate_hash?: string | null;
          expires_at?: string | null;
          external_id?: string | null;
          favorite_count?: number;
          id?: string;
          image_url?: string | null;
          images?: string[];
          previous_price?: number | null;
          published_at?: string;
          savings_amount?: number | null;
          scheduled_for?: string | null;
          shipping_info?: string | null;
          short_description?: string | null;
          slug?: string;
          source?: Database["public"]["Enums"]["deal_source"];
          source_url?: string | null;
          status?: Database["public"]["Enums"]["deal_status"];
          store_id?: string | null;
          subcategory_id?: string | null;
          temperature?: number;
          title?: string;
          updated_at?: string;
          votes_down?: number;
          votes_up?: number;
        };
        Relationships: [
          {
            foreignKeyName: "deals_category_id_fkey";
            columns: ["category_id"];
            isOneToOne: false;
            referencedRelation: "categories";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "deals_store_id_fkey";
            columns: ["store_id"];
            isOneToOne: false;
            referencedRelation: "stores";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "deals_subcategory_id_fkey";
            columns: ["subcategory_id"];
            isOneToOne: false;
            referencedRelation: "categories";
            referencedColumns: ["id"];
          },
        ];
      };
      favorites: {
        Row: {
          created_at: string;
          deal_id: string;
          id: string;
          user_id: string;
        };
        Insert: {
          created_at?: string;
          deal_id: string;
          id?: string;
          user_id: string;
        };
        Update: {
          created_at?: string;
          deal_id?: string;
          id?: string;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "favorites_deal_id_fkey";
            columns: ["deal_id"];
            isOneToOne: false;
            referencedRelation: "deals";
            referencedColumns: ["id"];
          },
        ];
      };
      import_logs: {
        Row: {
          finished_at: string | null;
          id: string;
          notes: string | null;
          source: Database["public"]["Enums"]["deal_source"];
          source_name: string | null;
          started_at: string;
          total_created: number;
          total_duplicates: number;
          total_errors: number;
          total_processed: number;
          total_updated: number;
        };
        Insert: {
          finished_at?: string | null;
          id?: string;
          notes?: string | null;
          source: Database["public"]["Enums"]["deal_source"];
          source_name?: string | null;
          started_at?: string;
          total_created?: number;
          total_duplicates?: number;
          total_errors?: number;
          total_processed?: number;
          total_updated?: number;
        };
        Update: {
          finished_at?: string | null;
          id?: string;
          notes?: string | null;
          source?: Database["public"]["Enums"]["deal_source"];
          source_name?: string | null;
          started_at?: string;
          total_created?: number;
          total_duplicates?: number;
          total_errors?: number;
          total_processed?: number;
          total_updated?: number;
        };
        Relationships: [];
      };
      notifications: {
        Row: {
          alert_id: string | null;
          body: string | null;
          created_at: string;
          deal_id: string | null;
          id: string;
          is_read: boolean;
          link_url: string | null;
          title: string;
          type: Database["public"]["Enums"]["notification_type"];
          user_id: string;
        };
        Insert: {
          alert_id?: string | null;
          body?: string | null;
          created_at?: string;
          deal_id?: string | null;
          id?: string;
          is_read?: boolean;
          link_url?: string | null;
          title: string;
          type: Database["public"]["Enums"]["notification_type"];
          user_id: string;
        };
        Update: {
          alert_id?: string | null;
          body?: string | null;
          created_at?: string;
          deal_id?: string | null;
          id?: string;
          is_read?: boolean;
          link_url?: string | null;
          title?: string;
          type?: Database["public"]["Enums"]["notification_type"];
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "notifications_alert_id_fkey";
            columns: ["alert_id"];
            isOneToOne: false;
            referencedRelation: "alerts";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "notifications_deal_id_fkey";
            columns: ["deal_id"];
            isOneToOne: false;
            referencedRelation: "deals";
            referencedColumns: ["id"];
          },
        ];
      };
      profiles: {
        Row: {
          avatar_url: string | null;
          bio: string | null;
          created_at: string;
          display_name: string | null;
          id: string;
          updated_at: string;
          user_id: string;
          username: string | null;
        };
        Insert: {
          avatar_url?: string | null;
          bio?: string | null;
          created_at?: string;
          display_name?: string | null;
          id?: string;
          updated_at?: string;
          user_id: string;
          username?: string | null;
        };
        Update: {
          avatar_url?: string | null;
          bio?: string | null;
          created_at?: string;
          display_name?: string | null;
          id?: string;
          updated_at?: string;
          user_id?: string;
          username?: string | null;
        };
        Relationships: [];
      };
      stores: {
        Row: {
          affiliate_id: string | null;
          affiliate_url_template: string | null;
          created_at: string;
          domain: string | null;
          id: string;
          is_active: boolean;
          logo_url: string | null;
          name: string;
          slug: string;
          updated_at: string;
        };
        Insert: {
          affiliate_id?: string | null;
          affiliate_url_template?: string | null;
          created_at?: string;
          domain?: string | null;
          id?: string;
          is_active?: boolean;
          logo_url?: string | null;
          name: string;
          slug: string;
          updated_at?: string;
        };
        Update: {
          affiliate_id?: string | null;
          affiliate_url_template?: string | null;
          created_at?: string;
          domain?: string | null;
          id?: string;
          is_active?: boolean;
          logo_url?: string | null;
          name?: string;
          slug?: string;
          updated_at?: string;
        };
        Relationships: [];
      };
      user_roles: {
        Row: {
          created_at: string;
          id: string;
          role: Database["public"]["Enums"]["app_role"];
          user_id: string;
        };
        Insert: {
          created_at?: string;
          id?: string;
          role: Database["public"]["Enums"]["app_role"];
          user_id: string;
        };
        Update: {
          created_at?: string;
          id?: string;
          role?: Database["public"]["Enums"]["app_role"];
          user_id?: string;
        };
        Relationships: [];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      get_user_stats: {
        Args: { _user_id: string };
        Returns: {
          comments_made: number;
          comments_received: number;
          deal_votes_cast: number;
          dislikes_received: number;
          favorites_count: number;
          likes_given: number;
          likes_received: number;
        }[];
      };
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"];
          _user_id: string;
        };
        Returns: boolean;
      };
      process_deal_statuses: { Args: never; Returns: undefined };
    };
    Enums: {
      alert_frequency: "instant" | "daily" | "weekly";
      app_role: "admin" | "user";
      deal_source: "manual" | "script" | "api" | "import";
      deal_status: "active" | "expired" | "scheduled" | "draft";
      notification_type: "alert_match" | "comment_reply" | "deal_expired" | "system";
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">;

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">];

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R;
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] & DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R;
      }
      ? R
      : never
    : never;

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I;
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I;
      }
      ? I
      : never
    : never;

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U;
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U;
      }
      ? U
      : never
    : never;

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never;

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never;

export const Constants = {
  public: {
    Enums: {
      alert_frequency: ["instant", "daily", "weekly"],
      app_role: ["admin", "user"],
      deal_source: ["manual", "script", "api", "import"],
      deal_status: ["active", "expired", "scheduled", "draft"],
      notification_type: ["alert_match", "comment_reply", "deal_expired", "system"],
    },
  },
} as const;
